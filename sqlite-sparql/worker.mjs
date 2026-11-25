// Web Worker for ../sqlite-sparql.html: runs SQLite's WASM build (with the sparqlite
// extension linked in) off the main thread, so a slow query never freezes the page.
//
// Messages in:  {id, type, ...args}   Replies: {id, ok: true, ...} | {id, ok: false, error}
//   init     {snapshot?}           open the database (from a snapshot, or load the example data)
//   query    {sql, bind, maxRows}  one statement with bound parameters -> {columns, rows, total}
//   script   {sql, maxRows}        any number of statements -> {results: [...]} (stops at an error)
//   load     {data, format, base, graph}   sparql_load()
//   export                         -> {bytes} (the whole database file)
//   import   {bytes}               replace the database with an uploaded SQLite file
//   reset    {empty}               back to the example dataset (or an empty store)
// Every reply that may have changed the database carries `snapshot` (the database bytes) so
// the page can restore it if it has to terminate a stuck worker.

// The OPFS VFSes are not used here; skip installing them (they would start a helper worker).
globalThis.sqlite3ApiConfig = {
  disable: { vfs: { opfs: true, 'opfs-vfs': true, 'opfs-sahpool': true, 'opfs-wl': true } },
};
// Imported dynamically so the config above is in place first. Not awaited at the top level:
// messages that arrive while a module worker is still evaluating would otherwise be lost.
const sqlite3Module = import('./sqlite3.mjs');

const DB_FILE = '/playground.sqlite';
const DATA = new URL('./data/', import.meta.url);
let sqlite3, db, capi, wasm;

async function fetchText(name) {
  const r = await fetch(new URL(name, DATA));
  if (!r.ok) throw new Error(`fetch ${name}: HTTP ${r.status}`);
  return r.text();
}

function openDb(bytes) {
  if (db) db.close();
  db = null;
  const name = wasm.allocCString(DB_FILE);
  try { wasm.exports.sqlite3__wasm_vfs_unlink(0, name); } finally { wasm.dealloc(name); }
  if (bytes) capi.sqlite3_js_posix_create_file(DB_FILE, bytes);
  // A file in Emscripten's in-memory filesystem rather than ':memory:', so sparqlite's
  // direct B-tree page reader is used (it needs a file database with a rollback journal).
  db = new sqlite3.oo1.DB(DB_FILE, 'c');
  // Guard rails for a browser tab: stop runaway queries and huge intermediate results.
  db.exec("SELECT sparql_config('timeout_ms', 20000), sparql_config('max_memory_mb', 256)");
}

async function loadExampleData() {
  const [languages, survey, jobs] = await Promise.all(
    ['languages.ttl', 'survey.trig', 'job_postings.sql'].map(fetchText));
  db.exec('PRAGMA page_size = 8192');
  db.exec('BEGIN');
  db.exec({ sql: "SELECT sparql_load(?, 'turtle')", bind: [languages] });
  db.exec({ sql: "SELECT sparql_load(?, 'trig')", bind: [survey] });
  db.exec(jobs);
  db.exec('COMMIT');
  db.exec('ANALYZE');
  db.exec('SELECT sparql_analyze()');
}

function stats() {
  const v = (sql) => db.selectValue(sql);
  return {
    quads: v('SELECT count(*) FROM rdf_quad'),
    terms: v('SELECT count(*) FROM rdf_term'),
    graphs: db.exec({
      sql: `SELECT v0 AS g, v1 AS n FROM sparql_rows('SELECT ?g (COUNT(*) AS ?n)
              WHERE { GRAPH ?g { ?s ?p ?o } } GROUP BY ?g ORDER BY ?g')`,
      rowMode: 'object', returnValue: 'resultRows',
    }),
    tables: db.exec({
      sql: `SELECT name FROM sqlite_schema WHERE type IN ('table', 'view')
              AND name NOT LIKE 'rdf\\_%' ESCAPE '\\' AND name NOT LIKE 'sqlite\\_%' ESCAPE '\\'
              ORDER BY name`,
      rowMode: 0, returnValue: 'resultRows',
    }),
    bytes: v('SELECT page_count * page_size FROM pragma_page_count, pragma_page_size'),
  };
}

function snapshot() {
  return capi.sqlite3_js_db_export(db.pointer);
}

function jsValue(pStmt, i) {
  const v = capi.sqlite3_value_to_js(capi.sqlite3_column_value(pStmt, i), false);
  if (typeof v === 'bigint') {
    return (v <= BigInt(Number.MAX_SAFE_INTEGER) && v >= BigInt(Number.MIN_SAFE_INTEGER)) ? Number(v) : v;
  }
  return v;
}

function errmsg() {
  return capi.sqlite3_errmsg(db.pointer);
}

// The first complete statement of `sql` (for error messages; prepare failed, so no tail).
function firstStatement(sql) {
  for (let i = sql.indexOf(';'); i >= 0; i = sql.indexOf(';', i + 1)) {
    if (capi.sqlite3_complete(sql.slice(0, i + 1))) return sql.slice(0, i + 1).trim();
  }
  return sql.trim();
}

// Runs every statement in `sqlText`, returning one result per statement. Stops at the first
// error, returning the results so far plus the error.
function runScript(sqlText, maxRows) {
  const results = [];
  const stack = wasm.scopedAllocPush();
  try {
    let len = wasm.jstrlen(sqlText);
    const ppStmt = wasm.scopedAlloc(2 * wasm.ptr.size + len + 1);
    const pzTail = wasm.ptr.add(ppStmt, wasm.ptr.size);
    let pSql = wasm.ptr.add(pzTail, wasm.ptr.size);
    const pEnd = wasm.ptr.add(pSql, len);
    wasm.jstrcpy(sqlText, wasm.heap8(), pSql, len, false);
    wasm.poke8(pEnd, 0);
    while (pSql && wasm.peek8(pSql)) {
      wasm.pokePtr([ppStmt, pzTail], 0);
      const rc = capi.sqlite3_prepare_v3(db.pointer, pSql, len, 0, ppStmt, pzTail);
      const pStmt = wasm.peekPtr(ppStmt);
      const start = pSql;
      pSql = wasm.peekPtr(pzTail);
      len = Number(wasm.ptr.add(pEnd, -pSql));
      if (rc) {
        return { results, error: errmsg(), failedSql: firstStatement(wasm.cstrToJs(start)) };
      }
      if (!pStmt) continue;
      const t0 = performance.now();
      const changesBefore = capi.sqlite3_total_changes(db.pointer);
      const sql = capi.sqlite3_sql(pStmt).trim();
      try {
        const ncol = capi.sqlite3_column_count(pStmt);
        const columns = [];
        for (let i = 0; i < ncol; i++) columns.push(capi.sqlite3_column_name(pStmt, i));
        const rows = [];
        let total = 0, step;
        while ((step = capi.sqlite3_step(pStmt)) === capi.SQLITE_ROW) {
          if (rows.length < maxRows) {
            const row = [];
            for (let i = 0; i < ncol; i++) row.push(jsValue(pStmt, i));
            rows.push(row);
          }
          total++;
        }
        if (step !== capi.SQLITE_DONE) {
          return { results, error: errmsg(), failedSql: sql };
        }
        const ms = performance.now() - t0;
        results.push(ncol ? { sql, columns, rows, total, ms }
                          : { sql, changes: capi.sqlite3_total_changes(db.pointer) - changesBefore, ms });
      } finally {
        capi.sqlite3_finalize(pStmt);
      }
    }
    return { results };
  } finally {
    wasm.scopedAllocPop(stack);
  }
}

function runQuery(sql, bind, maxRows) {
  const columns = [];
  const rows = [];
  let total = 0;
  db.exec({
    sql, bind, rowMode: 'array', columnNames: columns,
    callback(row) {
      if (rows.length < maxRows) rows.push(row.map(v => typeof v === 'bigint' && v <= BigInt(Number.MAX_SAFE_INTEGER) && v >= BigInt(Number.MIN_SAFE_INTEGER) ? Number(v) : v));
      total++;
    },
  });
  return { columns, rows, total };
}

const handlers = {
  async init({ snapshot: bytes }) {
    const t0 = performance.now();
    if (!sqlite3) {
      const { default: sqlite3InitModule } = await sqlite3Module;
      sqlite3 = await sqlite3InitModule();
      capi = sqlite3.capi;
      wasm = sqlite3.wasm;
    }
    openDb(bytes);
    if (!bytes) await loadExampleData();
    return {
      version: db.selectValue('SELECT sparql_version()'),
      sqliteVersion: capi.sqlite3_libversion(),
      ms: performance.now() - t0,
      stats: stats(),
      snapshot: bytes ? undefined : snapshot(),
    };
  },
  query({ sql, bind, maxRows = 1000, write }) {
    const t0 = performance.now();
    const before = capi.sqlite3_total_changes(db.pointer);
    const out = runQuery(sql, bind, maxRows);
    out.ms = performance.now() - t0;
    if (write || capi.sqlite3_total_changes(db.pointer) !== before) {
      out.stats = stats();
      out.snapshot = snapshot();
    }
    return out;
  },
  script({ sql, maxRows = 1000 }) {
    const t0 = performance.now();
    const out = runScript(sql, maxRows);
    out.ms = performance.now() - t0;
    out.stats = stats();
    out.snapshot = snapshot();
    return out;
  },
  load({ data, format, base, graph }) {
    const t0 = performance.now();
    const n = db.selectValue('SELECT sparql_load(?, ?, ?, ?)', [data, format || null, base || null, graph || null]);
    return { added: n, ms: performance.now() - t0, stats: stats(), snapshot: snapshot() };
  },
  export() {
    return { bytes: snapshot() };
  },
  import({ bytes }) {
    openDb(new Uint8Array(bytes));
    const state = db.selectValue("SELECT value FROM sparql_status WHERE key = 'schema_state'");
    return { stats: stats(), schemaState: state, snapshot: snapshot() };
  },
  async reset({ empty }) {
    openDb(null);
    if (!empty) await loadExampleData();
    else db.selectValue('SELECT sparql_init()');
    return { stats: stats(), snapshot: snapshot() };
  },
};

async function handle({ id, type, ...args }) {
  try {
    const result = await handlers[type](args);
    const transfer = [];
    for (const k of ['snapshot', 'bytes']) if (result && result[k]) transfer.push(result[k].buffer);
    self.postMessage({ id, ok: true, ...result }, transfer);
  } catch (e) {
    self.postMessage({ id, ok: false, error: e.message || String(e) });
  }
}

// One request at a time, in the order they arrive.
let queue = Promise.resolve();
self.onmessage = ({ data }) => { queue = queue.then(() => handle(data)); };

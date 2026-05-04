/* wasm_entry.c — JS-callable entry points.
 *
 * The JS playground builds an argv blob in WASM memory and calls
 * wasm_dispatch(); we wrap each argv entry into a Redis robj backed by an sds
 * string, look up the matching *Command function from the array branch's
 * t_array.c, and let it run. After the command returns, the JS side reads the
 * tagged reply buffer with wasm_reply_buf() / wasm_reply_len().
 */

#include "server.h"
#include "sds.h"
#include <emscripten.h>
#include <string.h>

void wasm_runtime_init(void);
void wasm_db_init(void);
redisDb *wasm_db(void);
void wasm_reply_reset(client *c);
uint8_t *wasm_reply_buf(client *c);
uint32_t wasm_reply_len(client *c);
void wasm_db_drop(const char *key, size_t klen);
void wasm_db_flush(void);
int wasm_db_stats(const char *key, size_t klen,
                  uint64_t *out_len, uint64_t *out_count, int64_t *out_cur,
                  uint64_t *out_alloc);

/* All AR* commands declared in t_array.c. */
void argetCommand(client *c);
void armgetCommand(client *c);
void arsetCommand(client *c);
void armsetCommand(client *c);
void ardelCommand(client *c);
void ardelrangeCommand(client *c);
void arlenCommand(client *c);
void arcountCommand(client *c);
void argetrangeCommand(client *c);
void arscanCommand(client *c);
void argrepCommand(client *c);
void aropCommand(client *c);
void arinsertCommand(client *c);
void arringCommand(client *c);
void arnextCommand(client *c);
void arseekCommand(client *c);
void arlastitemsCommand(client *c);
void arinfoCommand(client *c);

/* arsetCommand is in t_array.c; the array branch uses a single function for
 * ARSET so we don't dispatch differently per command. The mapping below is
 * by index into the JS-side command table. */
typedef void (*arCommandFn)(client *c);

static arCommandFn cmd_table[] = {
    argetCommand,        /* 0  ARGET     */
    armgetCommand,       /* 1  ARMGET    */
    arsetCommand,        /* 2  ARSET     */
    armsetCommand,       /* 3  ARMSET    */
    ardelCommand,        /* 4  ARDEL     */
    ardelrangeCommand,   /* 5  ARDELRANGE */
    arlenCommand,        /* 6  ARLEN     */
    arcountCommand,      /* 7  ARCOUNT   */
    argetrangeCommand,   /* 8  ARGETRANGE */
    arscanCommand,       /* 9  ARSCAN    */
    argrepCommand,       /* 10 ARGREP    */
    aropCommand,         /* 11 AROP      */
    arinsertCommand,     /* 12 ARINSERT  */
    arringCommand,       /* 13 ARRING    */
    arnextCommand,       /* 14 ARNEXT    */
    arseekCommand,       /* 15 ARSEEK    */
    arlastitemsCommand,  /* 16 ARLASTITEMS */
    arinfoCommand,       /* 17 ARINFO    */
};
static const int cmd_count = sizeof(cmd_table) / sizeof(cmd_table[0]);

/* The single client we run every command against. We reuse it across calls;
 * argv is rebuilt per dispatch. */
static client G_CLIENT;
static int G_INIT = 0;

EMSCRIPTEN_KEEPALIVE
void wasm_init(void) {
    if (G_INIT) return;
    wasm_runtime_init();
    wasm_db_init();
    G_CLIENT.db = wasm_db();
    G_CLIENT.argc = 0;
    G_CLIENT.argv = NULL;
    G_CLIENT.reply.buf = NULL;
    G_CLIENT.reply.len = 0;
    G_CLIENT.reply.cap = 0;
    G_INIT = 1;
}

/* Argv blob layout (little-endian):
 *   u32 argc
 *   for each arg: u32 len, bytes
 */

EMSCRIPTEN_KEEPALIVE
int wasm_dispatch(int cmd_index, const uint8_t *argv_blob, uint32_t blob_len) {
    if (cmd_index < 0 || cmd_index >= cmd_count) return -1;
    if (blob_len < 4) return -1;
    uint32_t argc;
    memcpy(&argc, argv_blob, 4);
    size_t off = 4;
    if (argc > 4096) return -1;  /* sanity */

    /* Build argv as robj* pointing at sds. */
    robj **argv = malloc(sizeof(robj *) * argc);
    robj *args = malloc(sizeof(robj) * argc);
    for (uint32_t i = 0; i < argc; i++) {
        if (off + 4 > blob_len) { /* malformed */ free(argv); free(args); return -1; }
        uint32_t len;
        memcpy(&len, argv_blob + off, 4);
        off += 4;
        if (off + len > blob_len) { free(argv); free(args); return -1; }
        sds s = sdsnewlen(argv_blob + off, len);
        off += len;
        args[i].type = OBJ_STRING;
        args[i].encoding = OBJ_ENCODING_RAW;
        args[i].ptr = s;
        argv[i] = &args[i];
    }

    G_CLIENT.argc = argc;
    G_CLIENT.argv = argv;
    wasm_reply_reset(&G_CLIENT);

    cmd_table[cmd_index](&G_CLIENT);

    /* Free argv. */
    for (uint32_t i = 0; i < argc; i++) sdsfree(args[i].ptr);
    free(argv);
    free(args);
    G_CLIENT.argc = 0;
    G_CLIENT.argv = NULL;
    return 0;
}

EMSCRIPTEN_KEEPALIVE
uint8_t *wasm_reply_buf_ptr(void) { return wasm_reply_buf(&G_CLIENT); }

EMSCRIPTEN_KEEPALIVE
uint32_t wasm_reply_buf_len(void) { return wasm_reply_len(&G_CLIENT); }

EMSCRIPTEN_KEEPALIVE
void wasm_drop_key(const uint8_t *key, uint32_t klen) {
    wasm_db_drop((const char *)key, klen);
}

EMSCRIPTEN_KEEPALIVE
void wasm_flush_all(void) { wasm_db_flush(); }

/* For the JS-side keyspace listing: caller passes a buffer; we write
 * (u32 num_keys) followed by each (u32 key_len, key bytes). Returns total
 * bytes written, or -1 if the buffer is too small. */
typedef struct { uint8_t *out; uint32_t cap; uint32_t pos; uint32_t count; int oom; } ListCtx;
extern void wasm_db_iter(void (*cb)(const char *, size_t, void *), void *);

static void list_keys_cb(const char *k, size_t n, void *vc) {
    ListCtx *c = vc;
    if (c->oom) return;
    if (c->pos + 4 + n > c->cap) { c->oom = 1; return; }
    uint32_t ln = (uint32_t)n;
    memcpy(c->out + c->pos, &ln, 4); c->pos += 4;
    memcpy(c->out + c->pos, k, n); c->pos += n;
    c->count++;
}

EMSCRIPTEN_KEEPALIVE
int wasm_list_keys(uint8_t *out, uint32_t out_size) {
    if (out_size < 4) return -1;
    ListCtx ctx = { out, out_size, 4, 0, 0 };
    wasm_db_iter(list_keys_cb, &ctx);
    if (ctx.oom) return -1;
    memcpy(ctx.out, &ctx.count, 4);
    return (int)ctx.pos;
}

/* Per-key stats for the side panel — separate call so JS can fetch quickly
 * without re-encoding via dispatch. */
EMSCRIPTEN_KEEPALIVE
int wasm_key_stats(const uint8_t *key, uint32_t klen, uint8_t *out, uint32_t out_size) {
    if (out_size < 32) return -1;
    uint64_t len, count, alloc;
    int64_t cur;
    if (!wasm_db_stats((const char *)key, klen, &len, &count, &cur, &alloc)) return 0;
    memcpy(out + 0, &len, 8);
    memcpy(out + 8, &count, 8);
    memcpy(out + 16, &cur, 8);
    memcpy(out + 24, &alloc, 8);
    return 1;
}

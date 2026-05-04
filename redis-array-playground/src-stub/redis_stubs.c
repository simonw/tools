/* redis_stubs.c — minimal Redis runtime for the WASM playground.
 *
 * Provides:
 *   - zmalloc with a length prefix (so sparsearray's alloc tracking works).
 *   - sds string lookups + a tiny in-memory keyspace.
 *   - a tagged binary reply buffer that t_array.c writes into via addReply*.
 *
 * The buffer wire format (each record):
 *
 *   byte type:
 *      0  nil
 *      1  simple string  (u32 len, bytes)
 *      2  error          (u32 len, bytes)
 *      3  signed integer (i64)
 *      4  unsigned int   (u64)
 *      5  bulk string    (u32 len, bytes)
 *      6  array          (u32 count, recursive elements)
 *      7  double         (8 bytes IEEE 754)
 *      8  map            (u32 count, recursive [k, v, ...] elements)
 *
 * Deferred arrays: addReplyDeferredLen() writes type 6 + a 4-byte placeholder
 * and returns the offset; setDeferredArrayLen() backpatches the placeholder.
 */

#include "server.h"
#include "sds.h"
#include "sdsalloc.h"
#include "fast_float_strtod.h"
#include "fpconv_dtoa.h"

#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <stdarg.h>
#include <math.h>

/* ============================================================================
 * zmalloc: malloc with a length prefix so sparsearray's alloc-size tracking
 * actually has something to read back.
 * ========================================================================= */

void *zmalloc(size_t size) {
    size_t *p = (size_t *)malloc(size + sizeof(size_t));
    if (!p) abort();
    p[0] = size;
    return (void *)(p + 1);
}
void *zcalloc(size_t size) {
    void *p = zmalloc(size);
    memset(p, 0, size);
    return p;
}
void *zrealloc(void *ptr, size_t size) {
    if (!ptr) return zmalloc(size);
    size_t *raw = ((size_t *)ptr) - 1;
    size_t *np = (size_t *)realloc(raw, size + sizeof(size_t));
    if (!np) abort();
    np[0] = size;
    return (void *)(np + 1);
}
void zfree(void *ptr) {
    if (!ptr) return;
    free(((size_t *)ptr) - 1);
}
size_t zmalloc_size(void *ptr) {
    if (!ptr) return 0;
    return ((size_t *)ptr)[-1] + sizeof(size_t);
}
size_t zmalloc_usable_size(void *ptr) { return zmalloc_size(ptr); }
/* sds.c expects an *_usable family that also returns the usable size. */
void *zmalloc_usable(size_t size, size_t *usable) {
    void *p = zmalloc(size);
    if (usable) *usable = zmalloc_size(p);
    return p;
}
void *ztrymalloc_usable(size_t size, size_t *usable) {
    return zmalloc_usable(size, usable);
}
void *zrealloc_usable(void *ptr, size_t size, size_t *usable, size_t *old_usable) {
    if (old_usable) *old_usable = ptr ? zmalloc_size(ptr) : 0;
    void *p = zrealloc(ptr, size);
    if (usable) *usable = zmalloc_size(p);
    return p;
}
/* redisassert.h uses _serverAssert via the SDS path. */
void _serverAssert(const char *estr, const char *file, int line) {
    fprintf(stderr, "ASSERT: %s @ %s:%d\n", estr, file, line);
    abort();
}

/* ============================================================================
 * Keyspace: tiny open-addressed table keyed by sds. The playground only ever
 * keeps a handful of array keys at once, so this is intentionally simple.
 * ========================================================================= */

typedef struct kvEntry { sds key; robj *val; } kvEntry;

#define KV_INITIAL_CAP 16

typedef struct kvDict {
    kvEntry *slots;
    size_t cap;
    size_t used;
} kvDict;

static kvDict *kvNew(void) {
    kvDict *d = zcalloc(sizeof(*d));
    d->cap = KV_INITIAL_CAP;
    d->slots = zcalloc(sizeof(kvEntry) * d->cap);
    return d;
}

static size_t kvHash(const char *s, size_t n) {
    /* FNV-1a — speed and quality both irrelevant at playground scale.
     * Compute in 64 bits then narrow to size_t (32-bit on wasm32). */
    uint64_t h = 1469598103934665603ULL;
    for (size_t i = 0; i < n; i++) { h ^= (unsigned char)s[i]; h *= 1099511628211ULL; }
    return (size_t)h;
}

static int kvSlot(kvDict *d, const char *k, size_t n, size_t *out) {
    size_t mask = d->cap - 1;
    size_t h = kvHash(k, n) & mask;
    for (size_t i = 0; i < d->cap; i++) {
        size_t pos = (h + i) & mask;
        if (d->slots[pos].key == NULL) { *out = pos; return 0; }
        if (sdslen(d->slots[pos].key) == n &&
            memcmp(d->slots[pos].key, k, n) == 0) { *out = pos; return 1; }
    }
    *out = 0;
    return 0;
}

static void kvGrow(kvDict *d) {
    size_t newcap = d->cap * 2;
    kvEntry *old = d->slots;
    size_t oldcap = d->cap;
    d->slots = zcalloc(sizeof(kvEntry) * newcap);
    d->cap = newcap;
    d->used = 0;
    for (size_t i = 0; i < oldcap; i++) {
        if (old[i].key) {
            size_t pos;
            kvSlot(d, old[i].key, sdslen(old[i].key), &pos);
            d->slots[pos] = old[i];
            d->used++;
        }
    }
    zfree(old);
}

static robj *kvGet(kvDict *d, sds key) {
    size_t pos;
    if (kvSlot(d, key, sdslen(key), &pos)) return d->slots[pos].val;
    return NULL;
}

static void kvPut(kvDict *d, sds key, robj *val) {
    if ((d->used + 1) * 2 > d->cap) kvGrow(d);
    size_t pos;
    if (kvSlot(d, key, sdslen(key), &pos)) {
        /* Replace */
        if (d->slots[pos].val) freeArrayObject(d->slots[pos].val);
        sdsfree(d->slots[pos].key);
    } else {
        d->used++;
    }
    d->slots[pos].key = sdsdup(key);
    d->slots[pos].val = val;
}

static int kvDel(kvDict *d, sds key) {
    size_t pos;
    if (!kvSlot(d, key, sdslen(key), &pos)) return 0;
    sdsfree(d->slots[pos].key);
    if (d->slots[pos].val) freeArrayObject(d->slots[pos].val);
    d->slots[pos].key = NULL;
    d->slots[pos].val = NULL;
    /* Backshift to keep linear probing valid. */
    size_t mask = d->cap - 1;
    size_t i = (pos + 1) & mask;
    while (d->slots[i].key) {
        kvEntry e = d->slots[i];
        d->slots[i].key = NULL;
        d->slots[i].val = NULL;
        size_t want;
        kvSlot(d, e.key, sdslen(e.key), &want);
        d->slots[want] = e;
        i = (i + 1) & mask;
    }
    d->used--;
    return 1;
}

/* The single playground database. */
static redisDb playground_db;

void wasm_db_init(void) {
    if (!playground_db.backend) {
        playground_db.backend = kvNew();
        playground_db.id = 0;
    }
}
redisDb *wasm_db(void) { return &playground_db; }

/* Iterate keys: used by the JS keyspace panel. Calls cb(key_data, key_len, ctx)
 * for every populated entry. */
typedef void (*wasm_db_iter_cb)(const char *key, size_t klen, void *ctx);
void wasm_db_iter(wasm_db_iter_cb cb, void *ctx) {
    kvDict *d = playground_db.backend;
    if (!d) return;
    for (size_t i = 0; i < d->cap; i++) {
        if (d->slots[i].key)
            cb(d->slots[i].key, sdslen(d->slots[i].key), ctx);
    }
}

void wasm_db_drop(const char *key, size_t klen) {
    kvDict *d = playground_db.backend;
    if (!d) return;
    sds tmp = sdsnewlen(key, klen);
    kvDel(d, tmp);
    sdsfree(tmp);
}

void wasm_db_flush(void) {
    kvDict *d = playground_db.backend;
    if (!d) return;
    for (size_t i = 0; i < d->cap; i++) {
        if (d->slots[i].key) {
            sdsfree(d->slots[i].key);
            if (d->slots[i].val) freeArrayObject(d->slots[i].val);
            d->slots[i].key = NULL;
            d->slots[i].val = NULL;
        }
    }
    d->used = 0;
}

/* Per-key stats for the side panel — pulled directly from the live array. */
int wasm_db_stats(const char *key, size_t klen,
                  uint64_t *out_len, uint64_t *out_count, int64_t *out_cur,
                  uint64_t *out_alloc) {
    kvDict *d = playground_db.backend;
    if (!d) return 0;
    sds tmp = sdsnewlen(key, klen);
    robj *o = kvGet(d, tmp);
    sdsfree(tmp);
    if (!o || o->type != OBJ_ARRAY) return 0;
    redisArray *ar = o->ptr;
    *out_len = arLen(ar);
    *out_count = arCount(ar);
    *out_cur = (ar->insert_idx == AR_INSERT_IDX_NONE) ? -1 : (int64_t)ar->insert_idx;
    *out_alloc = ar->alloc_size;
    return 1;
}

/* ============================================================================
 * Reply buffer: typed, length-prefixed, designed for cheap JS decode.
 * ========================================================================= */

#define REPLY_NIL    0
#define REPLY_SIMPLE 1
#define REPLY_ERROR  2
#define REPLY_INT    3
#define REPLY_UINT   4
#define REPLY_BULK   5
#define REPLY_ARRAY  6
#define REPLY_DOUBLE 7
#define REPLY_MAP    8

static void rbReserve(redisReplyBuf *r, size_t need) {
    if (r->len + need <= r->cap) return;
    size_t cap = r->cap ? r->cap : 256;
    while (cap < r->len + need) cap *= 2;
    r->buf = realloc(r->buf, cap);
    r->cap = cap;
}
static void rbWrite(redisReplyBuf *r, const void *p, size_t n) {
    rbReserve(r, n);
    memcpy(r->buf + r->len, p, n);
    r->len += n;
}
static void rbU8(redisReplyBuf *r, uint8_t v) { rbWrite(r, &v, 1); }
static void rbU32(redisReplyBuf *r, uint32_t v) { rbWrite(r, &v, 4); }
static void rbI64(redisReplyBuf *r, int64_t v) { rbWrite(r, &v, 8); }
static void rbU64(redisReplyBuf *r, uint64_t v) { rbWrite(r, &v, 8); }
static void rbF64(redisReplyBuf *r, double v) { rbWrite(r, &v, 8); }

void wasm_reply_reset(client *c) {
    c->reply.len = 0;
}
uint8_t *wasm_reply_buf(client *c) { return c->reply.buf; }
uint32_t wasm_reply_len(client *c) { return (uint32_t)c->reply.len; }

void addReplyNull(client *c) { rbU8(&c->reply, REPLY_NIL); }

void addReplyError(client *c, const char *err) {
    rbU8(&c->reply, REPLY_ERROR);
    size_t n = strlen(err);
    rbU32(&c->reply, (uint32_t)n);
    rbWrite(&c->reply, err, n);
}
void addReplyErrorObject(client *c, robj *err) {
    sds s = err->ptr;
    rbU8(&c->reply, REPLY_ERROR);
    rbU32(&c->reply, (uint32_t)sdslen(s));
    rbWrite(&c->reply, s, sdslen(s));
}
void addReplyErrorFormat(client *c, const char *fmt, ...) {
    char tmp[512];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(tmp, sizeof(tmp), fmt, ap);
    va_end(ap);
    if (n < 0) n = 0;
    if ((size_t)n >= sizeof(tmp)) n = (int)sizeof(tmp) - 1;
    rbU8(&c->reply, REPLY_ERROR);
    rbU32(&c->reply, (uint32_t)n);
    rbWrite(&c->reply, tmp, n);
}
void addReplyErrorArity(client *c) {
    addReplyError(c, "wrong number of arguments");
}

void addReplyLongLong(client *c, long long ll) {
    rbU8(&c->reply, REPLY_INT);
    rbI64(&c->reply, ll);
}
void addReplyUnsignedLongLong(client *c, unsigned long long ull) {
    rbU8(&c->reply, REPLY_UINT);
    rbU64(&c->reply, ull);
}
void addReplyDouble(client *c, double d) {
    rbU8(&c->reply, REPLY_DOUBLE);
    rbF64(&c->reply, d);
}

void addReplyArrayLen(client *c, long length) {
    rbU8(&c->reply, REPLY_ARRAY);
    rbU32(&c->reply, (uint32_t)length);
}
void addReplyMapLen(client *c, long length) {
    rbU8(&c->reply, REPLY_MAP);
    rbU32(&c->reply, (uint32_t)length);
}

void addReplyBulkCBuffer(client *c, const void *p, size_t len) {
    rbU8(&c->reply, REPLY_BULK);
    rbU32(&c->reply, (uint32_t)len);
    rbWrite(&c->reply, p, len);
}
void addReplyBulkCString(client *c, const char *s) {
    addReplyBulkCBuffer(c, s, strlen(s));
}

/* Deferred reply: write the array tag + a 4-byte placeholder, return the
 * offset of the placeholder so setDeferredArrayLen can patch it. */
void *addReplyDeferredLen(client *c) {
    rbU8(&c->reply, REPLY_ARRAY);
    rbReserve(&c->reply, 4);
    size_t off = c->reply.len;
    uint32_t z = 0;
    rbWrite(&c->reply, &z, 4);
    return (void *)(uintptr_t)(off + 1);  /* +1 so we can recognise NULL */
}
void setDeferredArrayLen(client *c, void *node, long length) {
    if (!node) return;
    size_t off = (size_t)(uintptr_t)node - 1;
    uint32_t n = (uint32_t)length;
    memcpy(c->reply.buf + off, &n, 4);
}
void setDeferredMapLen(client *c, void *node, long length) {
    if (!node) return;
    size_t off = (size_t)(uintptr_t)node - 1;
    /* The leading tag byte was already a REPLY_ARRAY; switch to map. */
    c->reply.buf[off - 4] = REPLY_MAP;  /* not actually used by t_array.c */
    uint32_t n = (uint32_t)length;
    memcpy(c->reply.buf + off, &n, 4);
}

/* Shared replies. */
static robj shared_czero_obj;
static robj shared_syntaxerr_obj;
sharedObjectsStruct shared;

/* ============================================================================
 * Keyspace lookups + array object lifecycle.
 * ========================================================================= */

robj *createObject(int type, void *ptr) {
    robj *o = zmalloc(sizeof(*o));
    o->type = type;
    o->encoding = OBJ_ENCODING_RAW;
    o->ptr = ptr;
    return o;
}

robj *createArrayObject(void) {
    robj *o = createObject(OBJ_ARRAY, arNew());
    o->encoding = OBJ_ENCODING_SLICED_ARRAY;
    return o;
}

void freeArrayObject(robj *o) {
    if (!o) return;
    if (o->type == OBJ_ARRAY && o->ptr) arFree(o->ptr);
    zfree(o);
}

void decrRefCount(robj *o) {
    if (!o) return;
    if (o == &shared_czero_obj || o == &shared_syntaxerr_obj) return;
    if (o->type == OBJ_ARRAY) freeArrayObject(o);
    else { if (o->ptr) sdsfree(o->ptr); zfree(o); }
}

int checkType(client *c, robj *o, int type) {
    if (o == NULL || o->type == type) return 0;
    addReplyError(c, "WRONGTYPE Operation against a key holding the wrong kind of value");
    return 1;
}

robj *lookupKeyRead(redisDb *db, robj *key) {
    return kvGet(db->backend, key->ptr);
}
robj *lookupKeyReadOrReply(client *c, robj *key, robj *reply) {
    robj *o = kvGet(c->db->backend, key->ptr);
    if (!o) {
        if (reply) addReplyErrorObject(c, reply);
        else addReplyNull(c);
    }
    return o;
}
robj *lookupKeyWrite(redisDb *db, robj *key) {
    return kvGet(db->backend, key->ptr);
}

void dbAdd(redisDb *db, robj *key, robj **valref) {
    kvPut(db->backend, key->ptr, *valref);
    /* Read it back so callers using *valref get the stored object. The shim
     * stores by value-copy of the pointer, so the same pointer is fine. */
}

/* Stubs that t_array.c calls but the playground doesn't care about. */
void signalModifiedKey(client *c, redisDb *db, robj *key) { UNUSED(c); UNUSED(db); UNUSED(key); }
void notifyKeyspaceEvent(int type, const char *event, robj *key, int dbid) {
    UNUSED(type); UNUSED(event); UNUSED(key); UNUSED(dbid);
}
void updateKeysizesHist(redisDb *db, int type, uint64_t before, int64_t after) {
    UNUSED(db); UNUSED(type); UNUSED(before); UNUSED(after);
}
size_t kvobjAllocSize(kvobj *kv) { UNUSED(kv); return 0; }
int getKeySlot(sds key) { UNUSED(key); return 0; }
void updateSlotAllocSize(redisDb *db, int slot, robj *o, size_t old_alloc, size_t new_alloc) {
    UNUSED(db); UNUSED(slot); UNUSED(o); UNUSED(old_alloc); UNUSED(new_alloc);
}
void keyModified(client *c, redisDb *db, robj *key, robj *o, int set) {
    UNUSED(c); UNUSED(db); UNUSED(key); UNUSED(o); UNUSED(set);
}
void dbDeleteSkipKeysizesUpdate(redisDb *db, robj *key) {
    sds k = key->ptr;
    kvDel(db->backend, k);
}

/* getLongLongFromObjectOrReply: parse argv[i] (sds) into long long. */
int getLongLongFromObjectOrReply(client *c, robj *o, long long *target,
                                 const char *msg) {
    sds s = o->ptr;
    long long v;
    if (string2ll(s, sdslen(s), &v)) {
        *target = v;
        return C_OK;
    }
    addReplyError(c, msg ? msg : "value is not an integer or out of range");
    return C_ERR;
}

/* ============================================================================
 * One-time setup.
 * ========================================================================= */

void wasm_runtime_init(void) {
    server.array_slice_size = AR_SLICE_SIZE_DEFAULT;
    server.array_sparse_kmax = AR_SPARSE_KMAX_DEFAULT;
    server.array_sparse_kmin = AR_SPARSE_KMIN_DEFAULT;
    server.dirty = 0;
    server.memory_tracking_enabled = 0;

    /* shared.czero is a bulk reply equivalent to ":0\r\n"; t_array.c only ever
     * uses it via lookupKeyReadOrReply(c, key, shared.czero), where we just
     * need any non-NULL robj. shared.syntaxerr is used via addReplyErrorObject
     * so it must contain a string. */
    shared_czero_obj.type = OBJ_STRING;
    shared_czero_obj.encoding = OBJ_ENCODING_RAW;
    shared_czero_obj.ptr = sdsnew("0");
    shared_syntaxerr_obj.type = OBJ_STRING;
    shared_syntaxerr_obj.encoding = OBJ_ENCODING_RAW;
    shared_syntaxerr_obj.ptr = sdsnew("syntax error");
    shared.czero = &shared_czero_obj;
    shared.syntaxerr = &shared_syntaxerr_obj;
}

/* server / sharedObjectsStruct definitions. */
redisServer server;

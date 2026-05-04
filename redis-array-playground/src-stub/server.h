/* server.h shim for the Redis Array WASM playground.
 *
 * t_array.c (the real, unmodified file from antirez:array) and util.c are
 * compiled against this header instead of the full Redis server.h. We declare
 * just the types and APIs they actually reference; everything else stays out.
 * The corresponding implementations live in redis_stubs.c. */

#ifndef __SERVER_SHIM_H
#define __SERVER_SHIM_H

#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <stdarg.h>
#include <errno.h>
#include <math.h>
#include <ctype.h>
#include <limits.h>

#include "sds.h"
#include "sparsearray.h"
#include "util.h"

#define UNUSED(x) ((void)(x))
#define ALWAYS_INLINE __attribute__((always_inline)) inline

/* Status codes */
#define C_OK 0
#define C_ERR -1

/* Object types */
#define OBJ_STRING 0
#define OBJ_ARRAY 8

/* Encodings (only the ones t_array.c references) */
#define OBJ_ENCODING_RAW 0
#define OBJ_ENCODING_INT 1
#define OBJ_ENCODING_EMBSTR 8
#define OBJ_ENCODING_SLICED_ARRAY 13

/* zmalloc family — backed by libc malloc with a length prefix so that
 * sparsearray's alloc tracking has something to read. */
void *zmalloc(size_t size);
void *zcalloc(size_t size);
void *zrealloc(void *ptr, size_t size);
void zfree(void *ptr);
size_t zmalloc_size(void *ptr);
size_t zmalloc_usable_size(void *ptr);

/* Number formatting / parsing — used both by sparsearray and t_array. */
int ll2string(char *s, size_t len, long long value);
int string2ll(const char *s, size_t slen, long long *value);
int string2ull(const char *s, unsigned long long *value);
int d2string(char *buf, size_t len, double value);
int string2d(const char *s, size_t slen, double *dp);

/* stringmatchlen powers GLOB matching in ARGREP. */
int stringmatchlen(const char *pattern, int patternLen,
                   const char *string, int stringLen, int nocase);

/* sds len — provided by sds.c which we link as-is. */

/* Minimal robj. Layout differs from the real Redis robj on purpose: we don't
 * need refcounts, LRU bits, or a kvobj overlay here, so a flat struct is
 * easier to keep in sync with the stubs. The set of fields t_array.c reads is
 * (encoding, ptr); we add type to round things out. */
typedef struct redisObject {
    int type;
    int encoding;
    void *ptr;
} robj, kvobj;

/* Minimal redisDb wrapper. The actual lookup is done via a small dict the
 * stub keeps in redis_stubs.c. */
typedef struct redisDb {
    void *backend;  /* opaque pointer to the in-memory key map */
    int id;
} redisDb;

/* Minimal client. addReply* writes typed reply records into c->reply.
 * The buffer format is the wire encoding consumed by the JS playground. */
typedef struct redisReplyBuf {
    uint8_t *buf;
    size_t len;
    size_t cap;
} redisReplyBuf;

typedef struct client {
    int argc;
    robj **argv;
    redisDb *db;
    redisReplyBuf reply;
} client;

/* Shared static replies referenced by t_array.c. */
typedef struct sharedObjectsStruct {
    robj *czero;
    robj *syntaxerr;
} sharedObjectsStruct;
extern sharedObjectsStruct shared;

/* Server-wide config / counters t_array.c and sparsearray.c read. */
typedef struct redisServer {
    /* sparsearray.c knobs */
    uint32_t array_slice_size;
    uint32_t array_sparse_kmax;
    uint32_t array_sparse_kmin;
    /* defrag stats — t_array.c never touches these but sparsearray.c does */
    long long stat_active_defrag_scanned;
    unsigned long active_defrag_max_scan_fields;
    /* t_array.c bumps server.dirty after every write */
    long long dirty;
    /* gates kvobjAllocSize() — we always leave this off */
    int memory_tracking_enabled;
} redisServer;
extern redisServer server;

/* Reply API (consumed only by t_array.c). All entry points eventually push a
 * tagged record onto c->reply. */
void addReplyNull(client *c);
void addReplyError(client *c, const char *err);
void addReplyErrorObject(client *c, robj *err);
void addReplyErrorFormat(client *c, const char *fmt, ...);
void addReplyErrorArity(client *c);
void addReplyLongLong(client *c, long long ll);
void addReplyUnsignedLongLong(client *c, unsigned long long ull);
void addReplyDouble(client *c, double d);
void addReplyArrayLen(client *c, long length);
void addReplyMapLen(client *c, long length);
void addReplyBulkCBuffer(client *c, const void *p, size_t len);
void addReplyBulkCString(client *c, const char *s);
void *addReplyDeferredLen(client *c);
void setDeferredArrayLen(client *c, void *node, long length);
void setDeferredMapLen(client *c, void *node, long length);
void addReplyArrayValue(client *c, void *v);  /* Defined in t_array.c. */

/* Argument parsing helpers t_array.c uses. */
int getLongLongFromObjectOrReply(client *c, robj *o, long long *target,
                                 const char *msg);

/* Object lifecycle (only what's needed for arrays/strings). */
robj *createObject(int type, void *ptr);
robj *createArrayObject(void);
void freeArrayObject(robj *o);
void decrRefCount(robj *o);
int checkType(client *c, robj *o, int type);

/* Keyspace lookup. db->backend is a small open-addressed dict in
 * redis_stubs.c keyed by sds. */
robj *lookupKeyRead(redisDb *db, robj *key);
robj *lookupKeyReadOrReply(client *c, robj *key, robj *reply);
robj *lookupKeyWrite(redisDb *db, robj *key);
void dbAdd(redisDb *db, robj *key, robj **valref);

/* These are all no-ops in the playground but t_array.c calls them. */
void signalModifiedKey(client *c, redisDb *db, robj *key);
void notifyKeyspaceEvent(int type, const char *event, robj *key, int dbid);
void updateKeysizesHist(redisDb *db, int type, uint64_t before, int64_t after);
size_t kvobjAllocSize(kvobj *kv);
int getKeySlot(sds key);
void updateSlotAllocSize(redisDb *db, int slot, robj *o, size_t old_alloc, size_t new_alloc);
void keyModified(client *c, redisDb *db, robj *key, robj *o, int set);
void dbDeleteSkipKeysizesUpdate(redisDb *db, robj *key);

/* notifyKeyspaceEvent classification flags (t_array.c references these). */
#define NOTIFY_GENERIC (1<<0)
#define NOTIFY_ARRAY   (1<<14)

/* serverAssert / serverPanic — same as before. */
#define serverAssert(_e) ((_e) ? (void)0 : (void)fprintf(stderr, "ASSERT: %s\n", #_e))
#define serverPanic(...) abort()

#endif

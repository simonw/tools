/*
 * WASM wrapper for Redis sparsearray.c (from antirez:array branch).
 *
 * Provides minimal stubs for the Redis runtime dependencies needed by
 * sparsearray.c, plus a small set of exported entry points the JS
 * playground can call to drive the AR* commands.
 */

#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <math.h>
#include <errno.h>
#include <emscripten.h>

/* Provide what server.h would normally pull in for sparsearray.c. */

/* Fake "server" struct used by the ArraySliceSize / ArraySparseKMax /
 * ArraySparseKMin / defrag-stat macros inside sparsearray.c. */
struct redisServer {
    uint32_t array_slice_size;
    uint32_t array_sparse_kmax;
    uint32_t array_sparse_kmin;
    long long stat_active_defrag_scanned;
    unsigned long active_defrag_max_scan_fields;
};
struct redisServer server;

#define ALWAYS_INLINE __attribute__((always_inline))

#define serverAssert(_e) ((_e) ? (void)0 : (void)fprintf(stderr, "ASSERT failed: %s\n", #_e))
#define serverPanic(...) abort()

/* zmalloc family: thin wrappers around malloc that track size via a
 * one-word prefix, so zmalloc_size() can recover it. WASM heap is small
 * but plenty for a playground. */
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

/* ll2string: Redis' fast int-to-string. We just use snprintf for the
 * playground; the algorithm doesn't matter for correctness. */
int ll2string(char *s, size_t len, long long value) {
    int n = snprintf(s, len, "%lld", value);
    if (n < 0) return 0;
    if ((size_t)n >= len) n = (int)len - 1;
    return n;
}

/* d2string: format a double like Redis does for arrays. %.17g preserves
 * round-trippable precision; we trim trailing zeros after a decimal
 * point so 1.0 stays as "1" not "1.00000000000000000". */
int d2string(char *buf, size_t len, double value) {
    if (isnan(value)) { snprintf(buf, len, "nan"); return 3; }
    if (isinf(value)) {
        if (value > 0) { snprintf(buf, len, "inf"); return 3; }
        snprintf(buf, len, "-inf"); return 4;
    }
    int n = snprintf(buf, len, "%.17g", value);
    if (n < 0) return 0;
    if ((size_t)n >= len) n = (int)len - 1;
    return n;
}

/* string2d: parse "%lf" with strtod, requiring full consumption. */
int string2d(const char *s, size_t slen, double *dp) {
    if (slen == 0 || slen > 511) return 0;
    char tmp[512];
    memcpy(tmp, s, slen);
    tmp[slen] = 0;
    char *end = NULL;
    errno = 0;
    double d = strtod(tmp, &end);
    if (errno == ERANGE) return 0;
    if (end == tmp || *end != 0) return 0;
    if (isnan(d)) return 0;
    *dp = d;
    return 1;
}

#define ULLONG_MAX_HALF 1844674407370955161ULL  /* (ULLONG_MAX / 10) */

/* string2ll: parse a base-10 long long, strict (no spaces, no trailing).
 * Returns 1 on success, 0 on failure. */
int string2ll(const char *s, size_t slen, long long *value) {
    if (slen == 0) return 0;
    size_t i = 0;
    int negative = 0;
    if (s[0] == '-') {
        if (slen == 1) return 0;
        negative = 1;
        i = 1;
    } else if (s[0] == '+') {
        if (slen == 1) return 0;
        i = 1;
    }
    if (s[i] == '0' && slen - i > 1) return 0;
    unsigned long long v = 0;
    while (i < slen) {
        char c = s[i++];
        if (c < '0' || c > '9') return 0;
        unsigned d = (unsigned)(c - '0');
        if (v > ULLONG_MAX_HALF || (v == ULLONG_MAX_HALF && d > 9)) return 0;
        v = v * 10 + d;
    }
    if (negative) {
        if (v > (unsigned long long)9223372036854775808ULL) return 0;
        *value = -(long long)v;
    } else {
        if (v > (unsigned long long)9223372036854775807ULL) return 0;
        *value = (long long)v;
    }
    return 1;
}

#include "sparsearray.h"

/* Configuration init: must be called once before using arNew(). */
EMSCRIPTEN_KEEPALIVE
void wasm_init(void) {
    server.array_slice_size = AR_SLICE_SIZE_DEFAULT;
    server.array_sparse_kmax = AR_SPARSE_KMAX_DEFAULT;
    server.array_sparse_kmin = AR_SPARSE_KMIN_DEFAULT;
    server.stat_active_defrag_scanned = 0;
    server.active_defrag_max_scan_fields = 0;
}

/* Wrappers exposed to JS. We use 32-bit indices in the JS layer (BigInt
 * is annoying); the playground will never exceed that. */

EMSCRIPTEN_KEEPALIVE
redisArray *wasm_ar_new(void) { return arNew(); }

EMSCRIPTEN_KEEPALIVE
void wasm_ar_free(redisArray *ar) { arFree(ar); }

EMSCRIPTEN_KEEPALIVE
uint32_t wasm_ar_count(redisArray *ar) { return (uint32_t)arCount(ar); }

EMSCRIPTEN_KEEPALIVE
uint32_t wasm_ar_len(redisArray *ar) { return (uint32_t)arLen(ar); }

/* Set a string-typed value at idx. Performs the same arEncode() that
 * Redis does so we get int / float / smallstr / arString automatically. */
EMSCRIPTEN_KEEPALIVE
void wasm_ar_set(redisArray *ar, uint32_t idx, const char *s, uint32_t len) {
    void *v = arEncode(s, (size_t)len);
    arSet(ar, (uint64_t)idx, v);
}

/* Promote-to-dense hint, useful before bulk ARSET-style ranges. */
EMSCRIPTEN_KEEPALIVE
void wasm_ar_promote_dense(redisArray *ar, uint32_t lo, uint32_t hi) {
    arMayPromoteToDenseForRangeSet(ar, lo, hi);
}

EMSCRIPTEN_KEEPALIVE
int wasm_ar_del(redisArray *ar, uint32_t idx) {
    return arDel(ar, (uint64_t)idx);
}

EMSCRIPTEN_KEEPALIVE
uint32_t wasm_ar_delete_range(redisArray *ar, uint32_t lo, uint32_t hi) {
    return (uint32_t)arDeleteRange(ar, lo, hi);
}

EMSCRIPTEN_KEEPALIVE
void wasm_ar_truncate(redisArray *ar, uint32_t limit) {
    arTruncate(ar, limit);
}

/* Decode a value at idx into a static buffer. Returns the decoded length
 * (>= 0), or -1 if the slot is empty. The caller reads bytes from the
 * pointer returned by wasm_ar_get_buf(). The buffer is reused on every
 * call, so JS must copy out before issuing another call. */
static char wasm_decode_buf[64];

EMSCRIPTEN_KEEPALIVE
char *wasm_ar_get_buf(void) { return wasm_decode_buf; }

EMSCRIPTEN_KEEPALIVE
int wasm_ar_get(redisArray *ar, uint32_t idx) {
    void *v = arGet(ar, (uint64_t)idx);
    if (v == NULL) return -1;
    size_t outlen = 0;
    const char *data = arDecode(v, wasm_decode_buf, sizeof(wasm_decode_buf), &outlen);
    if (data == NULL) return -1;
    /* For pointer (arString) data, copy into wasm_decode_buf so the JS
     * side always reads from the same buffer. arString values can be up
     * to 64 bytes here without losing the test value; longer values are
     * truncated. The playground caps input length anyway. */
    if (data != wasm_decode_buf) {
        size_t n = outlen < sizeof(wasm_decode_buf) - 1 ? outlen : sizeof(wasm_decode_buf) - 1;
        memcpy(wasm_decode_buf, data, n);
        wasm_decode_buf[n] = 0;
        return (int)n;
    }
    return (int)outlen;
}

/* For arString values longer than the static buffer, JS can call this
 * to query the raw string length first. */
EMSCRIPTEN_KEEPALIVE
int wasm_ar_value_len(redisArray *ar, uint32_t idx) {
    void *v = arGet(ar, (uint64_t)idx);
    if (v == NULL) return -1;
    /* Use arDecode to compute the length consistently with wasm_ar_get. */
    char tmp[64];
    size_t outlen = 0;
    const char *data = arDecode(v, tmp, sizeof(tmp), &outlen);
    (void)data;
    return (int)outlen;
}

/* Iteration: just naive indexed scan, fine for a playground. Returns
 * the next non-empty index >= start that is <= end, or -1 if none.
 * Use repeatedly to walk a range. */
EMSCRIPTEN_KEEPALIVE
int wasm_ar_next_index(redisArray *ar, uint32_t start, uint32_t end) {
    uint64_t len = arLen(ar);
    if (start > end) return -1;
    if ((uint64_t)end >= len) end = (len > 0) ? (uint32_t)(len - 1) : 0;
    if (len == 0) return -1;
    for (uint32_t i = start; i <= end; i++) {
        void *v = arGet(ar, (uint64_t)i);
        if (v != NULL) return (int)i;
        if (i == end) break;
    }
    return -1;
}

/* Quick stats getters for the UI. */
EMSCRIPTEN_KEEPALIVE
uint32_t wasm_ar_alloc_size(redisArray *ar) { return (uint32_t)ar->alloc_size; }

EMSCRIPTEN_KEEPALIVE
uint32_t wasm_ar_num_slices(redisArray *ar) { return (uint32_t)ar->num_slices; }

EMSCRIPTEN_KEEPALIVE
uint32_t wasm_ar_slice_size(redisArray *ar) { return ar->slice_size; }

/* Insert-cursor accessors: insert_idx is what ARNEXT / ARSEEK / ARINSERT /
 * ARRING / ARLASTITEMS rely on. We use -1 as the JS sentinel for the
 * AR_INSERT_IDX_NONE "no inserts yet" state. */
EMSCRIPTEN_KEEPALIVE
int wasm_ar_get_insert_idx(redisArray *ar) {
    if (ar->insert_idx == AR_INSERT_IDX_NONE) return -1;
    if (ar->insert_idx > 0x7fffffff) return 0x7fffffff;
    return (int)ar->insert_idx;
}

EMSCRIPTEN_KEEPALIVE
void wasm_ar_set_insert_idx(redisArray *ar, int idx) {
    if (idx < 0) ar->insert_idx = AR_INSERT_IDX_NONE;
    else ar->insert_idx = (uint64_t)idx;
}

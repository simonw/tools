/* Minimal stub of server.h for WASM-only builds of sparsearray.c.
 * Only declares the symbols sparsearray.c references. */

#ifndef __SERVER_H_STUB
#define __SERVER_H_STUB

#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

#define ALWAYS_INLINE __attribute__((always_inline))

void *zmalloc(size_t size);
void *zcalloc(size_t size);
void *zrealloc(void *ptr, size_t size);
void zfree(void *ptr);
size_t zmalloc_size(void *ptr);
size_t zmalloc_usable_size(void *ptr);

int ll2string(char *s, size_t len, long long value);
int string2ll(const char *s, size_t slen, long long *value);
int d2string(char *buf, size_t len, double value);
int string2d(const char *s, size_t slen, double *dp);

#define UNUSED(x) ((void)(x))

struct redisServer {
    uint32_t array_slice_size;
    uint32_t array_sparse_kmax;
    uint32_t array_sparse_kmin;
    long long stat_active_defrag_scanned;
    unsigned long active_defrag_max_scan_fields;
};
extern struct redisServer server;

#define serverAssert(_e) ((_e) ? (void)0 : (void)fprintf(stderr, "ASSERT: %s\n", #_e))
#define serverPanic(...) abort()

#include "sparsearray.h"

#endif

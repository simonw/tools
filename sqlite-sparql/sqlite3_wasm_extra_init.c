/*
** Compiled into sqlite3.wasm by SQLite's ext/wasm build, which calls
** sqlite3_wasm_extra_init() once from sqlite3_initialize(). It registers
** the sparqlite Rust extension (linked in from libsparqlite_wasm.a) as an
** auto-extension, so every connection opened from JavaScript gets the
** sparql_* functions and virtual tables.
*/
#include "sqlite3.h"

extern int sqlite3_sparqlite_init(sqlite3 *, char **, const void *);

int sqlite3_wasm_extra_init(const char *z){
  (void)z;
  return sqlite3_auto_extension((void (*)(void))sqlite3_sparqlite_init);
}

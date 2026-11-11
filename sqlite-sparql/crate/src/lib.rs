//! sparqlite statically linked into SQLite's WASM build.
//!
//! `sqlite3_wasm_extra_init()` (../sqlite3_wasm_extra_init.c, compiled into sqlite3.wasm)
//! registers `sqlite3_sparqlite_init` with `sqlite3_auto_extension`, so every connection the
//! JavaScript API opens gets the sparql_* functions and virtual tables.
use rusqlite::{Connection, ffi};
use std::os::raw::{c_char, c_int, c_void};

fn init(db: *mut ffi::sqlite3) -> rusqlite::Result<()> {
    // from_handle: the Connection does not own (or close) the handle.
    let conn = unsafe { Connection::from_handle(db) }?;
    sq_api::register(&conn)
}

/// Writes `msg` to `*pz_err_msg` as a sqlite3_malloc'd string (SQLite frees it).
unsafe fn set_error(pz_err_msg: *mut *mut c_char, msg: &str) {
    if pz_err_msg.is_null() {
        return;
    }
    let bytes = msg.as_bytes();
    let p = unsafe { ffi::sqlite3_malloc((bytes.len() + 1) as c_int) } as *mut u8;
    if !p.is_null() {
        unsafe {
            std::ptr::copy_nonoverlapping(bytes.as_ptr(), p, bytes.len());
            *p.add(bytes.len()) = 0;
            *pz_err_msg = p as *mut c_char;
        }
    }
}

/// Auto-extension entry point. The third argument is NULL in SQLite's WASM build (it is
/// compiled with SQLITE_OMIT_LOAD_EXTENSION) and is not needed here.
///
/// # Safety
/// Called by SQLite with a valid, open connection.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn sqlite3_sparqlite_init(
    db: *mut ffi::sqlite3,
    pz_err_msg: *mut *mut c_char,
    _p_api: *const c_void,
) -> c_int {
    match std::panic::catch_unwind(|| init(db)) {
        Ok(Ok(())) => ffi::SQLITE_OK,
        Ok(Err(e)) => {
            unsafe { set_error(pz_err_msg, &format!("sparqlite: {e}")) };
            ffi::SQLITE_ERROR
        }
        Err(_) => {
            unsafe { set_error(pz_err_msg, "sparqlite: panic during registration") };
            ffi::SQLITE_ERROR
        }
    }
}

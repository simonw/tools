# Third-Party Libraries and Assets

This directory contains third-party software components used in the SLOCCount web application.

## WebPerl (v0.09-beta)

**WebPerl** is a WebAssembly port of Perl 5, allowing Perl code to run in web browsers.

- **Author**: Hauke Dämpfling (haukex@zero-g.net)
- **Institution**: Leibniz Institute of Freshwater Ecology and Inland Fisheries (IGB), Berlin, Germany
- **Copyright**: © 2018 Hauke Dämpfling
- **Source**: https://github.com/haukex/webperl
- **Website**: http://webperl.zero-g.net
- **Version**: v0.09-beta (prebuilt release from March 3, 2019)

### License

WebPerl is dual-licensed under the same terms as Perl 5 itself:

- **GNU General Public License** (GPL) version 1 or later, OR
- **Artistic License** (which comes with Perl 5)

You may choose either license. See `webperl/LICENSE_gpl.txt` and `webperl/LICENSE_artistic.txt` for full license texts.

### Files Included

- `webperl.js` - Main WebPerl loader
- `emperl.js` - Emscripten-compiled Perl JavaScript
- `emperl.wasm` - WebAssembly Perl binary
- `emperl.data` - Perl runtime data files
- `LICENSE_artistic.txt` - Artistic License text
- `LICENSE_gpl.txt` - GNU GPL text

---

## SLOCCount

**SLOCCount** (Source Lines of Code Count) is a suite of programs for counting physical source lines of code (SLOC) in large software systems.

- **Original Author**: David A. Wheeler (dwheeler@dwheeler.com)
- **Maintainer**: Jeff Licquia
- **Copyright**: © 2001-2004 David A. Wheeler
- **Source**: https://github.com/licquia/sloccount
- **Commit Used**: `7220ff627334a8f646617fe0fa542d401fb5287e`

### License

SLOCCount is licensed under the **GNU General Public License version 2** (GPL-2.0).

### Files Included

- `sloccount-perl.zip` - Archive containing the Perl scripts from SLOCCount that implement the actual line counting algorithms

The zip file includes various language-specific counting scripts (e.g., `python_count`, `c_count`, `perl_count`) and supporting utilities.

---

## Attribution

This SLOCCount web application makes use of:

1. **WebPerl** for running Perl in the browser via WebAssembly
2. **SLOCCount Perl scripts** for accurate source line counting with comment filtering

Both projects are used in accordance with their respective open-source licenses. No modifications have been made to the WebPerl runtime or SLOCCount scripts themselves.

## Compliance Notes

- WebPerl runtime files are distributed as-is from the official prebuilt v0.09-beta release
- SLOCCount scripts are loaded from the official repository commit `7220ff6`
- License files are preserved in their original locations
- This application is a web interface that uses these tools, not a modification of them

## More Information

- **WebPerl Documentation**: http://webperl.zero-g.net/using.html
- **SLOCCount Documentation**: https://github.com/licquia/sloccount/blob/master/README
- **COCOMO Cost Model**: The cost estimation feature uses the Basic COCOMO model as implemented in the original SLOCCount tool

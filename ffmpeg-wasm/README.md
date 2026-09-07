# ffmpeg-wasm

Vendored copy of the UMD build of [`@ffmpeg/ffmpeg`](https://github.com/ffmpegwasm/ffmpeg.wasm) 0.12.15 (MIT license).

- `ffmpeg.js` - the `FFmpegWASM` wrapper class
- `814.ffmpeg.js` - the Web Worker the wrapper spawns

These two small files are served from this origin because browsers refuse to
start a Web Worker from a cross-origin (CDN) URL. The much larger
`@ffmpeg/core` files (`ffmpeg-core.js` and the ~32 MB `ffmpeg-core.wasm`)
are loaded from jsDelivr at runtime by the tools that use them.

Used by `video-compressor.html`.

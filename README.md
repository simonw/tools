# tools.joostvanderlaan.nl

Miscellaneous HTML+JavaScript tools built mostly with the help of LLMs. See also [/python/](https://tools.joostvanderlaan.nl/python/) for tools written using Python.

This collection is an experiment in prompt-driven development with very low stakes.

The [colophon](https://tools.joostvanderlaan.nl/colophon) lists commit messages and transcripts for every tool.

The code lives in [javdl/tools](https://github.com/javdl/tools).

<!-- recently starts -->
<!-- recently stops -->

## Image and media
- [Social media cropper](https://tools.joostvanderlaan.nl/social-media-cropper) crop images to 2×1 for social sharing
- [Image resize and quality comparison](https://tools.joostvanderlaan.nl/image-resize-quality) compare JPEG quality settings
- [Image to JPEG](https://tools.joostvanderlaan.nl/image-to-jpeg) convert PNG or WebP files to JPEG
- [Image to SVG](https://tools.joostvanderlaan.nl/image-to-svg) trace bitmap images to SVG paths
- [SVG to JPEG/PNG](https://tools.joostvanderlaan.nl/svg-render) render an SVG to a raster image
- [SVG sandbox](https://tools.joostvanderlaan.nl/svg-sandbox) display decoded SVG files safely
- [SVG progressive render](https://tools.joostvanderlaan.nl/svg-progressive-render) watch an SVG draw itself
- [BBox cropper](https://tools.joostvanderlaan.nl/bbox-cropper) draw bounding boxes and read the coordinates
- [Mask visualizer](https://tools.joostvanderlaan.nl/mask-visualizer) inspect JSON masks with bounding boxes
- [FFmpeg crop helper](https://tools.joostvanderlaan.nl/ffmpeg-crop) generate FFmpeg commands for cropped videos
- [TIFF orientation viewer](https://tools.joostvanderlaan.nl/tiff-orientation) inspect EXIF orientation metadata
- [Avatar web component](https://tools.joostvanderlaan.nl/avatar-web-component) upload and crop avatars in place
- [YouTube Thumbnails](https://tools.joostvanderlaan.nl/youtube-thumbnails) list thumbnail URLs for a video

## Text and document
- [OCR](https://tools.joostvanderlaan.nl/ocr) recognize text from images and PDFs in your browser
- [PDF OCR](https://tools.joostvanderlaan.nl/pdf-ocr) run optical character recognition on uploaded PDFs
- [Compare PDFs](https://tools.joostvanderlaan.nl/compare-pdfs) visualize differences between two PDFs
- [Render Markdown](https://tools.joostvanderlaan.nl/render-markdown) convert Markdown to HTML using the GitHub API
- [HTML preview](https://tools.joostvanderlaan.nl/html-preview) type HTML on the left and see it rendered on the right
- [RTF to HTML](https://tools.joostvanderlaan.nl/rtf-to-html) inspect RTF clipboard data and convert it to HTML
- [Markdown math](https://tools.joostvanderlaan.nl/markdown-math) live preview of Markdown with LaTeX equations
- [Footnotes experiment](https://tools.joostvanderlaan.nl/footnotes-experiment) demo linking footnotes to popups
- [Reading time calculator](https://tools.joostvanderlaan.nl/reading-time) estimate how long text will take to read
- [Word counter](https://tools.joostvanderlaan.nl/word-counter) count words across multiple text blocks
- [Text wrap balance nav](https://tools.joostvanderlaan.nl/text-wrap-balance-nav) explore the `text-wrap: balance` property
- [Navigation for headings](https://tools.joostvanderlaan.nl/nav-for-headings) generate an ID-based table of contents
- [Paste rich text](https://tools.joostvanderlaan.nl/paste-rich-text) inspect HTML and plain text on your clipboard
- [Paste HTML subset](https://tools.joostvanderlaan.nl/paste-html-subset) see which tags survive HTML sanitization
- [Clipboard viewer](https://tools.joostvanderlaan.nl/clipboard-viewer) debug everything stored in your clipboard
- [Extract URLs](https://tools.joostvanderlaan.nl/extract-urls) pull a list of links from pasted HTML
- [JSON to Markdown transcript](https://tools.joostvanderlaan.nl/json-to-markdown-transcript) convert transcript JSON to Markdown
- [JSON to YAML](https://tools.joostvanderlaan.nl/json-to-yaml) convert between JSON and YAML formats
- [YAML Explorer](https://tools.joostvanderlaan.nl/yaml-explorer) browse YAML documents in a collapsible tree
- [JSON schema builder](https://tools.joostvanderlaan.nl/json-schema-builder) visually design a JSON schema
- [Incomplete JSON printer](https://tools.joostvanderlaan.nl/incomplete-json-printer) pretty print partial JSON documents
- [PHP Deserializer](https://tools.joostvanderlaan.nl/php-deserializer) turn serialized PHP into JSON
- [SQL Pretty Printer](https://tools.joostvanderlaan.nl/sql-pretty-printer) reformat SQL queries for readability
- [Pipfile.lock parser](https://tools.joostvanderlaan.nl/pipfile) extract dependency versions from `Pipfile.lock`

## Data and time utilities
- [Timestamp Converter](https://tools.joostvanderlaan.nl/unix-timestamp) convert Unix timestamps to readable dates
- [Timezones](https://tools.joostvanderlaan.nl/timezones) compare times across multiple time zones
- [Date calculator](https://tools.joostvanderlaan.nl/date-calculator) count days between dates or only weekdays
- [Transfer time estimator](https://tools.joostvanderlaan.nl/transfer-time) work out how long file transfers will take
- [Token usage calculator](https://tools.joostvanderlaan.nl/token-usage) summarize LLM token logs by model
- [LLM prices redirect](https://tools.joostvanderlaan.nl/llm-prices) quick link to the latest model pricing site
- [CSV marker map](https://tools.joostvanderlaan.nl/csv-marker-map) plot markers on a map from a CSV file
- [Species observation map](https://tools.joostvanderlaan.nl/species-observation-map) browse recent iNaturalist sightings

## GitHub and development
- [GitHub API write](https://tools.joostvanderlaan.nl/github-api-write) upload text or images directly to a repo
- [GitHub issue viewer](https://tools.joostvanderlaan.nl/github-issue) fetch GitHub issues and comments
- [GitHub issue to Markdown](https://tools.joostvanderlaan.nl/github-issue-to-markdown) turn an issue thread into Markdown
- [Zip/Wheel explorer](https://tools.joostvanderlaan.nl/zip-wheel-explorer) view the contents of Python wheels and zips
- [Ares phonetic alphabet](https://tools.joostvanderlaan.nl/ares) convert text to the ARES emergency phonetic code
- [Code with Claude 2025](https://tools.joostvanderlaan.nl/code-with-claude-2025) prototype workflow for Claude coding
- [Side panel dialog demo](https://tools.joostvanderlaan.nl/side-panel-dialog) experiment with the HTML `dialog` element
- [Broadcast channel chat](https://tools.joostvanderlaan.nl/broadcast-channel-chat) chat across tabs using BroadcastChannel

## Bluesky and social tools
- [Bluesky WebSocket Firehose](https://tools.joostvanderlaan.nl/bluesky-firehose) watch real-time activity on Bluesky
- [Bluesky resolve DID](https://tools.joostvanderlaan.nl/bluesky-resolve) convert a handle like `simonwillison.net` into a DID
- [Bluesky timeline](https://tools.joostvanderlaan.nl/bluesky-timeline) view a user’s recent posts and replies
- [Bluesky thread export](https://tools.joostvanderlaan.nl/bluesky-thread) save a Bluesky thread to Markdown
- [Bluesky quote finder](https://tools.joostvanderlaan.nl/bluesky-quote-finder) find all quotes of a Bluesky post
- [Event planner](https://tools.joostvanderlaan.nl/event-planner) rough schedule planner stored in localStorage
- [Passkeys demo](https://tools.joostvanderlaan.nl/passkeys) experiment with browser-based passkey authentication

## LLM playgrounds and debuggers
- [Haiku](https://tools.joostvanderlaan.nl/haiku) generate haikus using Claude Haiku and your webcam
- [Chrome Prompt Playground](https://tools.joostvanderlaan.nl/chrome-prompt-playground) run prompts on Chrome’s Gemini Nano
- [Gemini bounding box visualizer](https://tools.joostvanderlaan.nl/gemini-bbox) visualize bounding boxes returned by Gemini
- [Gemini chat client](https://tools.joostvanderlaan.nl/gemini-chat) simple chat UI for the Gemini API
- [Gemini mask visualizer](https://tools.joostvanderlaan.nl/gemini-mask) overlay segmentation masks from Gemini
- [Gemini image JSON renderer](https://tools.joostvanderlaan.nl/gemini-image-json) display images from Gemini JSON output
- [Claude Token Counter](https://tools.joostvanderlaan.nl/claude-token-counter) count tokens for Claude prompts
- [OpenAI audio input](https://tools.joostvanderlaan.nl/openai-audio) record and send audio to OpenAI models
- [OpenAI audio output](https://tools.joostvanderlaan.nl/openai-audio-output) generate speech with OpenAI voices
- [OpenAI WebRTC demo](https://tools.joostvanderlaan.nl/openai-webrtc) interact with OpenAI’s real-time audio API
- [GPT-4o Gist audio player](https://tools.joostvanderlaan.nl/gpt-4o-audio-player) play audio responses stored on GitHub Gist
- [JSON schema builder](https://tools.joostvanderlaan.nl/json-schema-builder) build JSON schemas with a visual editor

## Miscellaneous
- [Arena animated](https://tools.joostvanderlaan.nl/arena-animated) animated chart of the LMSYS Chatbot Arena
- [California Clock Change](https://tools.joostvanderlaan.nl/california-clock-change) see when daylight saving time changes
- [Open Sauce 2025 schedule](https://tools.joostvanderlaan.nl/open-sauce-2025) browse the upcoming conference sessions
- [OpenFreeMap demo](https://tools.joostvanderlaan.nl/openfreemap-demo) MapLibre demo with random points in San Francisco
- [Progress of the US presidency](https://tools.joostvanderlaan.nl/progress) track days elapsed in the current term
- [User Agent display](https://tools.joostvanderlaan.nl/user-agent) show your browser’s user agent string
- [Encrypt / decrypt message](https://tools.joostvanderlaan.nl/encrypt) share short encrypted messages
- [ARIA live regions](https://tools.joostvanderlaan.nl/aria-live-regions) demo of dynamic page announcements
- [Prompts.js](https://tools.joostvanderlaan.nl/prompts-js) small library for nicer JavaScript prompts
- [APSW SQLite query explainer](https://tools.joostvanderlaan.nl/apsw-query) explain SQLite queries using APSW

## On Observable

On [Observable](https://observablehq.com/):

- [Blog to newsletter](https://observablehq.com/@simonw/blog-to-newsletter) helps turn blog posts into a newsletter
- [Convert Claude JSON to Markdown](https://observablehq.com/@simonw/convert-claude-json-to-markdown) for sharing Claude transcripts
- [Hacker News homepage with links to comments ordered by most recent first](https://observablehq.com/@simonw/hacker-news-homepage)

<script type="module" src="homepage-search.js" data-tool-search></script>

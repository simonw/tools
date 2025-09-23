# tools.simonwillison.net

Miscellaneous HTML+JavaScript tools built mostly with the help of LLMs.

This collection is an experiment in prompt-driven development with very low stakes.

The [colophon](https://tools.simonwillison.net/colophon) lists commit messages and transcripts for every tool.

The code lives in [simonw/tools](https://github.com/simonw/tools) and many tools used the Claude custom instructions [described here](https://simonwillison.net/2024/Dec/19/one-shot-python-tools/#custom-instructions).

## Image and media
- [Social media cropper](https://tools.simonwillison.net/social-media-cropper) crop images to 2×1 for social sharing
- [Image resize and quality comparison](https://tools.simonwillison.net/image-resize-quality) compare JPEG quality settings
- [Image to JPEG](https://tools.simonwillison.net/image-to-jpeg) convert PNG or WebP files to JPEG
- [Image to SVG](https://tools.simonwillison.net/image-to-svg) trace bitmap images to SVG paths
- [SVG to JPEG/PNG](https://tools.simonwillison.net/svg-render) render an SVG to a raster image
- [SVG sandbox](https://tools.simonwillison.net/svg-sandbox) display decoded SVG files safely
- [SVG progressive render](https://tools.simonwillison.net/svg-progressive-render) watch an SVG draw itself
- [BBox cropper](https://tools.simonwillison.net/bbox-cropper) draw bounding boxes and read the coordinates
- [Mask visualizer](https://tools.simonwillison.net/mask-visualizer) inspect JSON masks with bounding boxes
- [FFmpeg crop helper](https://tools.simonwillison.net/ffmpeg-crop) generate FFmpeg commands for cropped videos
- [TIFF orientation viewer](https://tools.simonwillison.net/tiff-orientation) inspect EXIF orientation metadata
- [Avatar web component](https://tools.simonwillison.net/avatar-web-component) upload and crop avatars in place
- [YouTube Thumbnails](https://tools.simonwillison.net/youtube-thumbnails) list thumbnail URLs for a video

## Text and document
- [OCR](https://tools.simonwillison.net/ocr) recognize text from images and PDFs in your browser
- [PDF OCR](https://tools.simonwillison.net/pdf-ocr) run optical character recognition on uploaded PDFs
- [Compare PDFs](https://tools.simonwillison.net/compare-pdfs) visualize differences between two PDFs
- [Render Markdown](https://tools.simonwillison.net/render-markdown) convert Markdown to HTML using the GitHub API
- [HTML preview](https://tools.simonwillison.net/html-preview) type HTML on the left and see it rendered on the right
- [RTF to HTML](https://tools.simonwillison.net/rtf-to-html) inspect RTF clipboard data and convert it to HTML
- [Markdown math](https://tools.simonwillison.net/markdown-math) live preview of Markdown with LaTeX equations
- [Footnotes experiment](https://tools.simonwillison.net/footnotes-experiment) demo linking footnotes to popups
- [Reading time calculator](https://tools.simonwillison.net/reading-time) estimate how long text will take to read
- [Word counter](https://tools.simonwillison.net/word-counter) count words across multiple text blocks
- [Text wrap balance nav](https://tools.simonwillison.net/text-wrap-balance-nav) explore the `text-wrap: balance` property
- [Navigation for headings](https://tools.simonwillison.net/nav-for-headings) generate an ID-based table of contents
- [Paste rich text](https://tools.simonwillison.net/paste-rich-text) inspect HTML and plain text on your clipboard
- [Paste HTML subset](https://tools.simonwillison.net/paste-html-subset) see which tags survive HTML sanitization
- [Clipboard viewer](https://tools.simonwillison.net/clipboard-viewer) debug everything stored in your clipboard
- [Extract URLs](https://tools.simonwillison.net/extract-urls) pull a list of links from pasted HTML
- [JSON to Markdown transcript](https://tools.simonwillison.net/json-to-markdown-transcript) convert transcript JSON to Markdown
- [JSON to YAML](https://tools.simonwillison.net/json-to-yaml) convert between JSON and YAML formats
- [YAML Explorer](https://tools.simonwillison.net/yaml-explorer) browse YAML documents in a collapsible tree
- [JSON schema builder](https://tools.simonwillison.net/json-schema-builder) visually design a JSON schema
- [Incomplete JSON printer](https://tools.simonwillison.net/incomplete-json-printer) pretty print partial JSON documents
- [PHP Deserializer](https://tools.simonwillison.net/php-deserializer) turn serialized PHP into JSON
- [SQL Pretty Printer](https://tools.simonwillison.net/sql-pretty-printer) reformat SQL queries for readability
- [Pipfile.lock parser](https://tools.simonwillison.net/pipfile) extract dependency versions from `Pipfile.lock`

## Data and time utilities
- [Timestamp Converter](https://tools.simonwillison.net/unix-timestamp) convert Unix timestamps to readable dates
- [Timezones](https://tools.simonwillison.net/timezones) compare times across multiple time zones
- [Date calculator](https://tools.simonwillison.net/date-calculator) count days between dates or only weekdays
- [Transfer time estimator](https://tools.simonwillison.net/transfer-time) work out how long file transfers will take
- [Token usage calculator](https://tools.simonwillison.net/token-usage) summarize LLM token logs by model
- [LLM prices redirect](https://tools.simonwillison.net/llm-prices) quick link to the latest model pricing site
- [CSV marker map](https://tools.simonwillison.net/csv-marker-map) plot markers on a map from a CSV file
- [Species observation map](https://tools.simonwillison.net/species-observation-map) browse recent iNaturalist sightings

## GitHub and development
- [GitHub API write](https://tools.simonwillison.net/github-api-write) upload text or images directly to a repo
- [GitHub issue viewer](https://tools.simonwillison.net/github-issue) fetch GitHub issues and comments
- [GitHub issue to Markdown](https://tools.simonwillison.net/github-issue-to-markdown) turn an issue thread into Markdown
- [Zip/Wheel explorer](https://tools.simonwillison.net/zip-wheel-explorer) view the contents of Python wheels and zips
- [Ares phonetic alphabet](https://tools.simonwillison.net/ares) convert text to the ARES emergency phonetic code
- [Code with Claude 2025](https://tools.simonwillison.net/code-with-claude-2025) prototype workflow for Claude coding
- [Side panel dialog demo](https://tools.simonwillison.net/side-panel-dialog) experiment with the HTML `dialog` element
- [Broadcast channel chat](https://tools.simonwillison.net/broadcast-channel-chat) chat across tabs using BroadcastChannel

## Bluesky and social tools
- [Bluesky WebSocket Firehose](https://tools.simonwillison.net/bluesky-firehose) watch real-time activity on Bluesky
- [Bluesky resolve DID](https://tools.simonwillison.net/bluesky-resolve) convert a handle like `simonwillison.net` into a DID
- [Bluesky timeline](https://tools.simonwillison.net/bluesky-timeline) view a user’s recent posts and replies
- [Bluesky thread export](https://tools.simonwillison.net/bluesky-thread) save a Bluesky thread to Markdown
- [Event planner](https://tools.simonwillison.net/event-planner) rough schedule planner stored in localStorage
- [Passkeys demo](https://tools.simonwillison.net/passkeys) experiment with browser-based passkey authentication

## LLM playgrounds and debuggers
- [Haiku](https://tools.simonwillison.net/haiku) generate haikus using Claude Haiku and your webcam
- [Chrome Prompt Playground](https://tools.simonwillison.net/chrome-prompt-playground) run prompts on Chrome’s Gemini Nano
- [Gemini bounding box visualizer](https://tools.simonwillison.net/gemini-bbox) visualize bounding boxes returned by Gemini
- [Gemini chat client](https://tools.simonwillison.net/gemini-chat) simple chat UI for the Gemini API
- [Gemini mask visualizer](https://tools.simonwillison.net/gemini-mask) overlay segmentation masks from Gemini
- [Gemini image JSON renderer](https://tools.simonwillison.net/gemini-image-json) display images from Gemini JSON output
- [Claude Token Counter](https://tools.simonwillison.net/claude-token-counter) count tokens for Claude prompts
- [OpenAI audio input](https://tools.simonwillison.net/openai-audio) record and send audio to OpenAI models
- [OpenAI audio output](https://tools.simonwillison.net/openai-audio-output) generate speech with OpenAI voices
- [OpenAI WebRTC demo](https://tools.simonwillison.net/openai-webrtc) interact with OpenAI’s real-time audio API
- [GPT-4o Gist audio player](https://tools.simonwillison.net/gpt-4o-audio-player) play audio responses stored on GitHub Gist
- [JSON schema builder](https://tools.simonwillison.net/json-schema-builder) build JSON schemas with a visual editor

## Miscellaneous
- [Arena animated](https://tools.simonwillison.net/arena-animated) animated chart of the LMSYS Chatbot Arena
- [California Clock Change](https://tools.simonwillison.net/california-clock-change) see when daylight saving time changes
- [Open Sauce 2025 schedule](https://tools.simonwillison.net/open-sauce-2025) browse the upcoming conference sessions
- [OpenFreeMap demo](https://tools.simonwillison.net/openfreemap-demo) MapLibre demo with random points in San Francisco
- [Progress of the US presidency](https://tools.simonwillison.net/progress) track days elapsed in the current term
- [User Agent display](https://tools.simonwillison.net/user-agent) show your browser’s user agent string
- [Encrypt / decrypt message](https://tools.simonwillison.net/encrypt) share short encrypted messages
- [ARIA live regions](https://tools.simonwillison.net/aria-live-regions) demo of dynamic page announcements
- [Prompts.js](https://tools.simonwillison.net/prompts-js) small library for nicer JavaScript prompts
- [APSW SQLite query explainer](https://tools.simonwillison.net/apsw-query) explain SQLite queries using APSW

## On Observable

On [Observable](https://observablehq.com/):

- [Blog to newsletter](https://observablehq.com/@simonw/blog-to-newsletter) helps turn blog posts into a newsletter
- [Convert Claude JSON to Markdown](https://observablehq.com/@simonw/convert-claude-json-to-markdown) for sharing Claude transcripts
- [Hacker News homepage with links to comments ordered by most recent first](https://observablehq.com/@simonw/hacker-news-homepage)

<script type="module" src="homepage-search.js" data-tool-search></script>

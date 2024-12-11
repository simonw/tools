# tools.simonwillison.net

Miscellaneous HTML+JavaScript tools I have built, almost all with the assistance of LLMs.

Prompts used are linked to from [the commit messages](https://github.com/simonw/tools/commits) for each tool.

[Everything I built with Claude Artifacts this week](https://simonwillison.net/2024/Oct/21/claude-artifacts/) describes how I built a lot of these.

## Tools

- [OCR](https://tools.simonwillison.net/ocr) for PDF files and images that runs entirely in your browser
- [Render Markdown](https://tools.simonwillison.net/render-markdown) renders Markdown to HTML using the GitHub Markdown API
- [Annotated presentation creator](https://til.simonwillison.net/tools/annotated-presentations) to help turn slides into an annotated presentation
- [Box shadow CSS generator](https://tools.simonwillison.net/box-shadow) generates the CSS for a box shadow with interactive settings
- [Compare PDFs](https://tools.simonwillison.net/compare-pdfs) provides a visual comparison of the pages of two PDF files
- [Image resize and quality comparison](https://tools.simonwillison.net/image-resize-quality) converts an image to JPEGs using a number of different quality settings so you can select the smallest file size that is still usefully legible ([how I built this](https://simonwillison.net/2024/Jul/26/image-resize-and-quality-comparison/))
- [YouTube Thumbnails](https://tools.simonwillison.net/youtube-thumbnails) - paste in the URL to a YouTube video, get back all of the URLs to thumbnail images of different sizes for that video
- [SVG to JPEG/PNG](https://tools.simonwillison.net/svg-render) - turn an SVG file into a rendered JPEG or PNG ([how I built this](https://simonwillison.net/2024/Oct/6/svg-to-jpg-png/))
- [Jina Reader](https://tools.simonwillison.net/jina-reader) - convert any URL to copyable Markdown using the [Jina Reader API](https://jina.ai/reader/)
- [Extract URLs](https://tools.simonwillison.net/extract-urls) - copy a section from a web page to your clipboard, paste it in here and get back a plain text list of all of the linked URLs from that section
- [EXIF Data Viewer](https://tools.simonwillison.net/exif) - view EXIF data for an image
- [MDN Browser Support Timelines](https://tools.simonwillison.net/mdn-timelines) - search for web features and view the browser support timeline pulled from [MDN](https://developer.mozilla.org/)
- [Timestamp Converter](https://tools.simonwillison.net/unix-timestamp) - convert between Unix timestamps and human-readable dates
- [Timezones](https://tools.simonwillison.net/timezones) - select two timezones to see a table comparing their times for the next 48 hours
- [Social media cropper](https://tools.simonwillison.net/social-media-cropper) - open or paste in an image, crop it to 2x1 and download a compressed JPEG for use as a social media card

## LLM playgrounds and debuggers

- [Haiku](https://tools.simonwillison.net/haiku) generates Haikus from your camera using Claude 3 Haiku
- [Chrome Prompt Playground](https://tools.simonwillison.net/chrome-prompt-playground) is a UI for running prompts through the Google Chrome Canary experimental Gemini Nano LLM and saving the results in local storage
- [Gemini API Image Bounding Box Visualizer](https://tools.simonwillison.net/gemini-bbox) - run prompts against Google Gemini models that return bounding box co-ordinates and visualize them against the original image, see [this post](https://simonwillison.net/2024/Aug/26/gemini-bounding-box-visualization/) for details
- [Claude Token Counter](https://tools.simonwillison.net/claude-token-counter) - counts the number of tokens in a Claude prompt
- [OpenAI audio input](https://tools.simonwillison.net/openai-audio) - record audio through the microphone and send it to OpenAI's audio model
- [OpenAI audio output](https://tools.simonwillison.net/openai-audio-output) - run prompts against OpenAI that produce audio output and listen to it or download it from the browser

## Miscellaneous

- [Arena animated](https://tools.simonwillison.net/arena-animated) animates the progression of the LMSYS Chatbot Arena, inspired by [this visualization](https://public.flourish.studio/visualisation/17992181/) by [Peter Gostev](https://www.linkedin.com/posts/peter-gostev_how-companies-llms-compare-over-the-course-activity-7196899934615257090-zilk) (via [Time-Winter-4319 on Reddit](https://www.reddit.com/r/LocalLLaMA/comments/1bp4j19/gpt4_is_no_longer_the_top_dog_timelapse_of/))
- [California Clock Change](https://tools.simonwillison.net/california-clock-change) - shows when the clocks will next change for daylight saving time in California
- [Bluesky WebSocket Firehose](https://tools.simonwillison.net/bluesky-firehose) showing a live firehose of Bluesky activity, [described here](https://simonwillison.net/2024/Nov/20/bluesky-websocket-firehose/)
- [Prompts.js](https://tools.simonwillison.net/prompts-js) small JavaScript library enabling `await Prompts.alert("hi")` and `await Prompts.confirm("Continue?")` and `await Prompts.prompt("Enter your name")` 

## On Observable

On [Observable](https://observablehq.com/):

- [Blog to newsletter](https://observablehq.com/@simonw/blog-to-newsletter) helps me turn my blog into a [newsletter](https://simonw.substack.com)
- [Weeknotes](https://observablehq.com/@simonw/weeknotes) helps me write my [weeknotes](https://simonwillison.net/tags/weeknotes/)
- [Convert Claude JSON to Markdown](https://observablehq.com/@simonw/convert-claude-json-to-markdown) for sharing Claude conversation transcripts
- [Hacker News homepage with links to comments ordered by most recent first](https://observablehq.com/@simonw/hacker-news-homepage)

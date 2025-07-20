# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "textual",
#     "llm",
# ]
# ///
import argparse
import asyncio
import sys
from textual.app import App, ComposeResult
from textual.widgets import Markdown
import llm


class MDApp(App):
    def __init__(self, prompt: str, model: str, usage: bool):
        super().__init__()
        self.prompt = prompt
        self.model = model
        self.usage = usage

    def compose(self):
        yield Markdown()

    async def on_mount(self):
        asyncio.create_task(self._stream())

    async def _stream(self):
        md = self.query_one(Markdown)
        model = llm.get_async_model(self.model)
        response = model.prompt(self.prompt)
        async for chunk in response:
            await md.append(chunk)
        # Append usage
        if self.usage:
            await md.append(f"\n\n**{await response.usage()}**")
        await asyncio.sleep(0.1)
        await self.exit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", help="Prompt")
    parser.add_argument("-m", "--model", default="gpt-4.1-nano", help="Model to use")
    parser.add_argument("-u", "--usage", action="store_true", help="Show usage")
    args = parser.parse_args()
    MDApp(args.prompt, args.model, args.usage).run(inline=True, inline_no_clear=True)

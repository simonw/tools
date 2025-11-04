#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = ["openai>=2.2.0", "typing-extensions", "click"]
# ///

"""
Generate an image with OpenAI’s image models (Click CLI).

- PROMPT is required.
- OUTFILE is optional; defaults to /tmp/image-<6-hex>.png.
- Flags are auto-derived by introspecting `OpenAI().images.generate` using
  typing.get_type_hints(include_extras=True), so Literal[...] choices appear
  in --help.
- -m/--model defaults to gpt-image-1-mini (not restricted).
- Prints the JSON (without "data") to stderr in yellow; saves image to OUTFILE.
- Adds "generation_time_in_s" to the printed JSON, measuring the API call duration.
"""

import json
import os
import secrets
import sys
import time
import typing as t
import types as pytypes
import typing_extensions as tx
from base64 import b64decode
from pathlib import Path
from inspect import signature
from typing import get_args, get_origin, get_type_hints

import click
from openai import OpenAI
from openai.resources.images import Images

# Some OpenAI SDKs use sentinel / helper types; we’ll try to import them to filter unions cleanly.
try:
    from openai._types import NotGiven, NotGivenType  # type: ignore
except Exception:  # pragma: no cover
    NotGiven = object  # type: ignore

    class NotGivenType: ...  # type: ignore


# ----------------------------- Introspection helpers -----------------------------


def _is_literal(ann) -> bool:
    return get_origin(ann) in (t.Literal, tx.Literal)


def _is_union(ann) -> bool:
    return get_origin(ann) in (t.Union, pytypes.UnionType)


def _is_optional(ann) -> bool:
    return _is_union(ann) and type(None) in get_args(ann)


def _skip_ann(ann) -> bool:
    # Skip NotGiven / sentinel types in unions.
    try:
        if ann is NotGiven or isinstance(ann, NotGivenType):
            return True
    except Exception:
        pass
    name = getattr(ann, "__name__", "") or str(ann)
    return "NotGiven" in name or "Omit" in name


def _unwrap_optional(ann):
    if _is_optional(ann):
        return tuple(a for a in get_args(ann) if a is not type(None))  # noqa: E721
    return (ann,)


def literal_choices(annotation) -> list[str]:
    """Extract all Literal[...] strings from (possibly nested) union/optional types."""
    out: list[str] = []
    seen: set[str] = set()

    def walk(ann):
        if isinstance(ann, str):
            return
        if _is_literal(ann):
            for a in get_args(ann):
                s = str(a)
                if s not in seen:
                    seen.add(s)
                    out.append(s)
            return
        if _is_union(ann):
            for sub in get_args(ann):
                if _skip_ann(sub):
                    continue
                walk(sub)
            return
        origin = get_origin(ann)
        if origin is not None:
            for sub in get_args(ann):
                walk(sub)

    for part in _unwrap_optional(annotation):
        if not _skip_ann(part):
            walk(part)
    return out


# ----------------------------- CLI construction -----------------------------

PARAMS = ["background", "moderation", "output_format", "quality", "size"]


def build_command() -> click.Command:
    # Resolve annotations properly (handles forward refs & __future__ annotations)
    images_mod_globals = sys.modules[Images.__module__].__dict__
    hints = get_type_hints(
        Images.generate, globalns=images_mod_globals, include_extras=True
    )

    # model choices are “known” but we don’t enforce them; we just show in help
    model_choices = literal_choices(hints.get("model", str))

    params: list[click.Parameter] = []

    # PROMPT (positional, required)
    params.append(click.Argument(["prompt"], metavar="PROMPT"))

    # OUTFILE (positional, optional)
    params.append(
        click.Argument(
            ["outfile"],
            required=False,
            type=click.Path(dir_okay=False, writable=True, path_type=Path),
            metavar="OUTFILE",
        )
    )

    # -m/--model (not restricted, but show known values)
    model_help = "Model to use"
    if model_choices:
        model_help += f" (known: {', '.join(model_choices)})"
    params.append(
        click.Option(
            ["-m", "--model"],
            default="gpt-image-1-mini",
            show_default=True,
            help=model_help,
        )
    )

    # Derive options (background/moderation/output_format/quality/size) with choices from Literal
    for name in PARAMS:
        ann = hints.get(name)
        label = name.replace("_", " ")
        if ann is None:
            params.append(
                click.Option([f"--{name.replace('_','-')}"], help=f"{label}.")
            )
            continue
        choices = literal_choices(ann)
        if choices:
            params.append(
                click.Option(
                    [f"--{name.replace('_','-')}"],
                    type=click.Choice(choices, case_sensitive=True),
                    help=f"{label}.",
                )
            )
        else:
            params.append(
                click.Option([f"--{name.replace('_','-')}"], help=f"{label}.")
            )

    @click.pass_context
    def callback(ctx: click.Context, **kw):
        if not os.getenv("OPENAI_API_KEY"):
            raise click.UsageError("OPENAI_API_KEY is not set")

        prompt: str = kw.pop("prompt")
        outfile: Path | None = kw.pop("outfile", None)
        model: str = kw.pop("model")

        if outfile is None:
            # Default: /tmp/image-<6 hex>.png
            outfile = Path(f"/tmp/image-{secrets.token_hex(3)}.png")
        outfile.parent.mkdir(parents=True, exist_ok=True)

        # Prepare kwargs for Images.generate (drop Nones)
        gen_kwargs = {"model": model}
        for p in PARAMS:
            v = kw.get(p, None)
            if v is not None:
                gen_kwargs[p] = v

        client = OpenAI()

        # ---- timing just the generation call ----
        t0 = time.perf_counter()
        resp = client.images.generate(prompt=prompt, **gen_kwargs)
        t1 = time.perf_counter()
        generation_time = float(t1 - t0)
        # -----------------------------------------

        # Pretty-print JSON (minus "data") to stderr in yellow
        payload = (
            resp.model_dump()
            if hasattr(resp, "model_dump")
            else json.loads(
                json.dumps(resp, default=lambda o: getattr(o, "__dict__", str(o)))
            )
        )
        payload.pop("data", None)
        payload["generation_time_in_s"] = generation_time
        click.secho(
            json.dumps(payload, indent=2, sort_keys=True), fg="yellow", err=True
        )

        # Save image bytes
        outfile.write_bytes(b64decode(resp.data[0].b64_json))
        click.echo(f"Saved {outfile.resolve()}")

    return click.Command(
        name="image",
        params=params,
        callback=callback,
        help=(
            "Generate an image with OpenAI image models.\n\n"
            "Positional args:\n"
            "  PROMPT   Text prompt describing the image to generate.\n"
            "  OUTFILE  Output file path (default: /tmp/image-XXXXXX.png)\n"
        ),
        context_settings={"help_option_names": ["-h", "--help"]},
    )


def main() -> None:
    build_command()()


if __name__ == "__main__":
    main()

#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = ["openai>=2.2.0", "typing-extensions", "click"]
# ///

"""
Generate an image with OpenAI’s image models (Click CLI).

- PROMPT is required.
- OUTFILE is optional; defaults to /tmp/image-<6-hex>.png.
- -i/--image (repeatable) takes a file path or URL to an existing image; when
  given, the prompt is applied as an edit to that image via `images.edit`.
- Flags are auto-derived by introspecting `OpenAI().images.generate` using
  typing.get_type_hints(include_extras=True), so Literal[...] choices appear
  in --help.
- -m/--model defaults to gpt-image-1-mini (not restricted).
- Prints the JSON (without "data") to stderr in yellow; saves image to OUTFILE.
- Adds "generation_time_in_s" to the printed JSON, measuring the API call duration.
"""

import json
import mimetypes
import os
import secrets
import sys
import time
import urllib.parse
import urllib.request
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


# ----------------------------- Input images -----------------------------

_IMAGE_EXTS = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}


def load_input_image(ref: str) -> tuple[str, bytes, str]:
    """Load an image from a local path or an http(s) URL.

    Returns a (filename, bytes, content_type) tuple suitable for the SDK.
    """
    if ref.startswith(("http://", "https://")):
        req = urllib.request.Request(ref, headers={"User-Agent": "openai_image.py"})
        try:
            with urllib.request.urlopen(req) as r:
                data = r.read()
                ctype = (r.headers.get_content_type() or "").lower()
        except Exception as e:
            raise click.BadParameter(f"could not fetch {ref}: {e}", param_hint="--image")
        name = os.path.basename(urllib.parse.urlsplit(ref).path) or "image"
        if not ctype.startswith("image/"):
            ctype = mimetypes.guess_type(name)[0] or "image/png"
        if not os.path.splitext(name)[1]:
            name += _IMAGE_EXTS.get(ctype, ".png")
        return name, data, ctype
    path = Path(ref).expanduser()
    if not path.is_file():
        raise click.BadParameter(f"file not found: {ref}", param_hint="--image")
    ctype = mimetypes.guess_type(path.name)[0] or "image/png"
    return path.name, path.read_bytes(), ctype


# ----------------------------- CLI construction -----------------------------

PARAMS = ["background", "moderation", "output_format", "quality"]
# Parameters accepted by images.edit but not images.generate
EDIT_ONLY_PARAMS = ["input_fidelity"]


def build_command() -> click.Command:
    # Resolve annotations properly (handles forward refs & __future__ annotations)
    images_mod_globals = sys.modules[Images.__module__].__dict__
    hints = get_type_hints(
        Images.generate, globalns=images_mod_globals, include_extras=True
    )
    edit_hints = get_type_hints(
        Images.edit, globalns=images_mod_globals, include_extras=True
    )

    # model choices are “known” but we don’t enforce them; we just show in help
    model_choices = literal_choices(hints.get("model", str))
    size_choices = literal_choices(hints.get("size", str))

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

    # -i/--image (repeatable): file path or URL to an existing image to edit
    params.append(
        click.Option(
            ["-i", "--image", "images"],
            multiple=True,
            metavar="PATH_OR_URL",
            help=(
                "Existing image to edit (file path or URL). May be repeated to "
                "supply multiple reference images. When given, the prompt is "
                "applied as an edit using the images.edit endpoint."
            ),
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

    # --size (not restricted, but show known values)
    size_help = "size"
    if size_choices:
        size_help += f" (known: {', '.join(size_choices)})"
    params.append(click.Option(["--size"], help=size_help))

    # Derive options (background/moderation/output_format/quality) with choices from Literal
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

    # Edit-only options (e.g. --input-fidelity), choices from images.edit Literals
    for name in EDIT_ONLY_PARAMS:
        ann = edit_hints.get(name)
        label = name.replace("_", " ")
        choices = literal_choices(ann) if ann is not None else []
        params.append(
            click.Option(
                [f"--{name.replace('_','-')}"],
                type=click.Choice(choices, case_sensitive=True) if choices else None,
                help=f"{label} (only used with --image).",
            )
        )

    @click.pass_context
    def callback(ctx: click.Context, **kw):
        if not os.getenv("OPENAI_API_KEY"):
            raise click.UsageError("OPENAI_API_KEY is not set")

        prompt: str = kw.pop("prompt")
        outfile: Path | None = kw.pop("outfile", None)
        images: tuple[str, ...] = kw.pop("images", ())
        model: str = kw.pop("model")
        size: str | None = kw.pop("size", None)

        if outfile is None:
            # Default: /tmp/image-<6 hex>.png
            outfile = Path(f"/tmp/image-{secrets.token_hex(3)}.png")
        outfile.parent.mkdir(parents=True, exist_ok=True)

        # Prepare kwargs for Images.generate (drop Nones)
        gen_kwargs = {"model": model}
        if size is not None:
            gen_kwargs["size"] = size
        for p in PARAMS:
            v = kw.get(p, None)
            if v is not None:
                gen_kwargs[p] = v

        if images:
            # Edit mode: drop params images.edit does not accept, add edit-only ones
            edit_params = signature(Images.edit).parameters
            for p in list(gen_kwargs):
                if p not in edit_params:
                    click.secho(
                        f"Warning: --{p.replace('_', '-')} is not supported with "
                        "--image, ignoring",
                        fg="red",
                        err=True,
                    )
                    gen_kwargs.pop(p)
            for p in EDIT_ONLY_PARAMS:
                v = kw.get(p, None)
                if v is not None:
                    gen_kwargs[p] = v
            loaded = [load_input_image(ref) for ref in images]
            gen_kwargs["image"] = loaded[0] if len(loaded) == 1 else loaded
        else:
            for p in EDIT_ONLY_PARAMS:
                if kw.get(p, None) is not None:
                    click.secho(
                        f"Warning: --{p.replace('_', '-')} only applies with "
                        "--image, ignoring",
                        fg="red",
                        err=True,
                    )

        client = OpenAI()

        # ---- timing just the generation call ----
        t0 = time.perf_counter()
        if images:
            resp = client.images.edit(prompt=prompt, **gen_kwargs)
        else:
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
            "Generate an image with OpenAI image models, or edit an existing "
            "image passed with -i/--image.\n\n"
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

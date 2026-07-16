//go:build js && wasm

// WebAssembly entry point for mermaid-ascii, the browser build behind
// ../mermaid-ascii.html. Copied into a checkout of
// https://github.com/AlexanderGrooff/mermaid-ascii by build_wasm.sh
// (as wasm/main.go) and compiled with GOOS=js GOARCH=wasm.
//
// It exposes a single function to JavaScript:
//
//	renderMermaidAscii(source, {ascii, styleType, direction,
//	                            paddingX, paddingY, borderPadding})
//	  -> {output: string} | {error: string}
//
// With styleType "html", colored text (mermaid classDef ... color:#hex)
// is wrapped in <span style='color: ...'> tags. The values inside those
// tags are NOT escaped by the library, so the page must sanitize the
// output rather than assigning it to innerHTML directly.
package main

import (
	"fmt"
	"syscall/js"

	"github.com/AlexanderGrooff/mermaid-ascii/cmd"
	"github.com/AlexanderGrooff/mermaid-ascii/pkg/diagram"
	"github.com/sirupsen/logrus"
)

func intOpt(opts js.Value, key string, fallback int) int {
	v := opts.Get(key)
	if v.Type() != js.TypeNumber {
		return fallback
	}
	return v.Int()
}

func render(this js.Value, args []js.Value) (result any) {
	// A panic would otherwise kill the Go runtime and leave the page with a
	// dead render function; recover turns it into a normal error result.
	defer func() {
		if r := recover(); r != nil {
			result = map[string]any{"error": fmt.Sprintf("renderer panic: %v", r)}
		}
	}()

	if len(args) < 1 {
		return map[string]any{"error": "missing mermaid source argument"}
	}
	source := args[0].String()

	config := diagram.DefaultConfig()
	if len(args) > 1 {
		opts := args[1]
		if !opts.IsUndefined() && !opts.IsNull() {
			if v := opts.Get("ascii"); v.Type() == js.TypeBoolean {
				config.UseAscii = v.Bool()
			}
			if v := opts.Get("direction"); v.Type() == js.TypeString {
				config.GraphDirection = v.String()
			}
			if v := opts.Get("styleType"); v.Type() == js.TypeString {
				config.StyleType = v.String()
			}
			config.PaddingBetweenX = intOpt(opts, "paddingX", config.PaddingBetweenX)
			config.PaddingBetweenY = intOpt(opts, "paddingY", config.PaddingBetweenY)
			config.BoxBorderPadding = intOpt(opts, "borderPadding", config.BoxBorderPadding)
		}
	}
	if err := config.Validate(); err != nil {
		return map[string]any{"error": err.Error()}
	}

	output, err := cmd.RenderDiagram(source, config)
	if err != nil {
		return map[string]any{"error": err.Error()}
	}
	return map[string]any{"output": output}
}

func main() {
	logrus.SetLevel(logrus.ErrorLevel)
	js.Global().Set("renderMermaidAscii", js.FuncOf(render))
	// Keep the Go runtime alive so the exported function stays callable.
	select {}
}

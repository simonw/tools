package cmd

// Globals normally declared in the upstream cmd/root.go, which build_wasm.sh
// removes from the WASM build because it drags in cobra (and cmd/web.go, which
// drags in gin). Defaults match root.go; the drawing code reads Coords
// directly, while the padding values are overridden per render from
// diagram.Config in GraphDiagram.Render.
var (
	Coords           bool
	boxBorderPadding = 1
	paddingBetweenX  = 5
	paddingBetweenY  = 5
)

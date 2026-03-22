# CRDT Merge State Visualizer

Explore how generation-counting conflict resolution works in distributed systems by editing two independent document branches and observing their deterministic merge. This interactive tool demonstrates the Manyana merge algorithm, where each state entry carries a count field that determines whether content is live (odd count) or deleted (even count)—allowing re-adds to automatically win over deletions during merge. Built with Python via Pyodide, it runs entirely in your browser with live rendering of merge trees, conflict detection, and detailed state inspection.

<!-- Generated from commit: 91ddc6c343064cca1482985e59603791ed1882cf -->
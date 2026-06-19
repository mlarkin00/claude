---
description: Generate a self-contained Cytoscape.js HTML graph of the OKF bundle. Nodes are concepts, edges are cross-links. Zero runtime deps — opens in any browser. Outputs viz.html by default.
---

Generate the bundle visualization.

```bash
python3 "$CLAUDE_PLUGIN_ROOT/scripts/okf_visualize.py" <bundle_root> [--out <path>] [--name <label>]
```

Load the `visualize` skill for the full implementation and viewer description.

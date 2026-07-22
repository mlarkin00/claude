---
type: Pitfall
title: Popping a patched module makes tests hit the network
description: sys.modules.pop() inside a test body discards the @patch-ed module, so
  the fresh import rebinds the real function and assertFalse(mock.called) passes vacuously.
tags:
- python
- testing
timestamp: '2026-07-22T21:49:59+00:00'
---

`@patch('mod.fn')` resolves and patches the module **at test start**. Calling
`sys.modules.pop('mod')` *inside* the test body throws that away; the subsequent
`import mod` builds a fresh, **unpatched** module.

## Two consequences

1. The test makes **real network calls** — the mock is no longer in the path.
2. Any `assertFalse(mock.called)` passes **vacuously**: an unpatched mock can never
   register a call, so the assertion cannot fail.

## Observed

Four `save_context` tests did this. Removing the in-test pops (a `tearDown` already
cleared the module) cut the suite from 13.2s to 2.9s — the speedup *is* the
evidence the network calls stopped — and turned one vacuous assertion into a real
one.

## Rule

Clear cached modules in `setUp`/`tearDown`, never inside a patched test body. And
when adding a regression test, **verify it fails against the pre-fix code** —
otherwise it documents the bug rather than guarding it. Related:
[payload key casing](../cross-runtime/payload-key-casing.md).

# Citations

[1] [mlarkin00/plugins](https://github.com/mlarkin00/plugins)

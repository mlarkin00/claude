---
name: index
description: Use when the user invokes /llm-wiki:index or asks to regenerate the index.md files in an OKF bundle. Runs okf_index.py for deterministic bottom-up index generation.
---

# /llm-wiki:index — Regenerate Bundle Indexes

Regenerates every `index.md` in an OKF bundle via a bottom-up walk. Groups entries by `type`, sorts alphabetically within each group, pulls `title` and `description` from each concept's frontmatter.

## Usage

```
/llm-wiki:index [path] [--llm]
```

`path` defaults to the nearest bundle root. `--llm` enables Gemini Flash directory descriptions (optional dep; default is deterministic).

## Steps

Run:
```bash
python3 <plugin_root>/scripts/okf_index.py <bundle_root>
# With LLM directory descriptions:
python3 <plugin_root>/scripts/okf_index.py <bundle_root> --llm
```

The script prints the list of written `index.md` paths to stdout and a summary to stderr.

Then refresh bundle discovery, because a host briefing file may hold an **inlined copy** of the root index (see `/llm-wiki:init`):

```bash
python3 <plugin_root>/scripts/okf_discover.py <bundle_root> --sync
```

`--sync` refreshes blocks that already exist and never creates one, so it is safe to run unconditionally. If it reports `skipped (no block …)` for every file, discovery was never installed — offer to run `okf_discover.py <bundle_root>` (no flag) to install it.

## What gets written

Each directory with `.md` files (excluding `index.md` itself) gets an `index.md` with this format:

```markdown
# BigQuery Dataset

* [Bitcoin Dataset](datasets/crypto_bitcoin.md) - Public blockchain data ETL'd from the Bitcoin network.

# BigQuery Table

* [Blocks](tables/blocks.md) - One row per block in the Bitcoin blockchain.
* [Transactions](tables/transactions.md) - One row per Bitcoin transaction.

# Subdirectories

* [references](references/index.md) - Contains 3 entries: metrics, joins, event_parameters.
```

## When to run

- After any batch of ingest (new/updated concept docs change what the index should contain).
- Before `/llm-wiki:visualize` (the visualizer reads concept frontmatter, not indexes, but fresh indexes help navigation).
- Before committing or sharing a bundle.

**Do not run during init** — there are no concept docs yet, so it has nothing to catalog. (It is safe against the seeded root: regeneration preserves the `okf_version` frontmatter that marks the bundle root.) Run it once the first concept docs are added.

## Claude-upgraded descriptions (optional)

With `--llm`, Gemini Flash generates one-sentence directory descriptions (e.g. "Three join references between the four core Bitcoin tables."). Without `--llm`, descriptions are deterministic ("Contains 3 entries: metrics, joins, event_parameters."). For most bundles, the deterministic form is sufficient; upgrade with `--llm` when you want richer navigation text.

Alternatively, after running `okf_index.py`, you (Claude) can rewrite specific directory descriptions inline by editing the affected `index.md` — the regenerated descriptions are plain text, not locked.

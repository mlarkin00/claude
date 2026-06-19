# {{BUNDLE_NAME}} — OKF Bundle

This is an OKF v0.1 knowledge bundle managed by the `llm-wiki` Claude Code plugin.

## Domain

<!-- Describe what this bundle covers. Example:
This bundle documents the BigQuery dataset `bigquery-public-data.crypto_bitcoin` — the
public Bitcoin blockchain data ETL'd by the bitcoin-etl project. -->

TODO: describe this bundle's domain.

## Directory structure

```
{{BUNDLE_DIR}}/
├── index.md              # auto-generated root catalog (do not edit by hand)
├── log.md                # chronological change log (use /llm-wiki:log to append)
├── CLAUDE.md             # this file — the "schema" that disciplines authoring
├── datasets/             # one doc per dataset
├── tables/               # one doc per table or shard family
├── references/           # reference docs: metrics/, joins/, dimensions, etc.
│   ├── metrics/          # one doc per aggregate metric (type: Reference, tags: [metric])
│   └── joins/            # one doc per table-pair join (type: Reference, tags: [join])
└── raw/                  # (optional) immutable source files — read-only inputs
```

## Type vocabulary

The `type` field in frontmatter must be one of:

<!-- Edit this list to match your bundle's domain. Examples: -->
- `BigQuery Dataset` — a top-level dataset
- `BigQuery Table` — a table or shard family
- `Reference` — a reusable reference doc (metrics, joins, enums, etc.)

<!-- For a general knowledge wiki, you might use: -->
<!-- - `Article` — a general knowledge concept -->
<!-- - `Q&A` — a filed query answer -->
<!-- - `Open Question` — a known gap to be filled -->

## Authoring conventions

- **Frontmatter**: `type` is required. Always include `title`, `description` (one tight sentence), and `resource` when there is an underlying asset.
- **Body order**: prose → `# Schema` (tables) → `# Common query patterns` (tables) → `# Citations`.
- **Cross-links**: file-relative paths only (e.g. `[users](../tables/users.md)` from `datasets/`). Never `/absolute/paths.md`.
- **Citations**: cite only URLs you actually fetched or know. Use `[N] [Title](URL)` format.
- **Descriptions**: one tight sentence used verbatim in `index.md`. Keep it informative and specific.

## Ingest instructions

<!-- Describe how to add new sources. Example: -->

To add a new BigQuery dataset:
```
/llm-wiki:ingest <project.dataset>
```

To add web documentation:
```
/llm-wiki:ingest https://...
# or with a seeds file:
/llm-wiki:ingest seeds.txt
```

## Maintenance

```
/llm-wiki:validate   # check §9 conformance
/llm-wiki:index      # regenerate index.md files after adding/changing docs
/llm-wiki:lint       # semantic health check
/llm-wiki:stats      # quick stats (orphans, broken links, citation coverage)
/llm-wiki:visualize  # generate viz.html graph
/llm-wiki:log        # append a dated entry to log.md
```

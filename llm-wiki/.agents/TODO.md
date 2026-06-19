# TODO

## P1 — Important / Unblocking

(none)

## P2 — Nice-to-Have

- [ ] **[P2]** Add `raw/` sources layer convention to `/llm-wiki:init` — scaffold a `raw/` subdirectory alongside the bundle and document the convention in `templates/bundle-CLAUDE.md`; currently unspecced (DESIGN.md §13).
- [ ] **[P2]** Implement multi-bundle repo detection — find nearest ancestor directory containing a root `index.md` with `okf_version: "0.1"` instead of requiring an explicit `<bundle_root>` argument (DESIGN.md §13).
- [ ] **[P2]** Add integration smoke test for augmentation guard — create a fixture bundle, write a doc with a known `# Schema` field count, then confirm `okf_doc.py write --web-pass` correctly blocks a shrink attempt.
- [ ] **[P2]** Add `--dry-run` to `okf_doc.py write` — preview what would be written without mutating disk; useful for agent debugging.
- [ ] **[P2]** Add shard-family wildcard display to `okf_bq.py list` output — currently lists every shard individually; collapse `prefix_YYYYMMDD` families to `prefix_*` with a count annotation.

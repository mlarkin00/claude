---
description: Ingest a source into an OKF bundle. Detects source type (URL → web crawl, project.dataset → BigQuery, file/dir → direct read) and runs the supervised ingest loop. Add --auto to skip review pauses.
---

Ingest one or more sources into the bundle using the supervised ingest loop.

Load the `ingest` skill and `ingesting-sources` skill for the full implementation.

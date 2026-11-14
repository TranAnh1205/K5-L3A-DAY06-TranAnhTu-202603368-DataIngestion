# Error and limitation log

| Stage | Observation | Action and remaining effect |
| --- | --- | --- |
| PDF extraction | The source has a blank physical page 17, figure-heavy pages, line wraps, replacement characters and footnotes embedded in body text. | Manifest excludes non-content pages; pipeline preserves page IDs and normalizes Unicode/whitespace. Some textual artifacts remain in chunks and quotes; no OCR was used. |
| Qdrant on Windows | One rerun failed with `PermissionError [WinError 5]` while Qdrant local tried to replace `meta.json` after deleting and recreating a collection. | Changed store re-ingestion to stable-ID upsert plus removal of stale points, avoiding delete/recreate on routine reruns. The same `.venv` command then completed with A=484 and B=C=549 points. The exact external file-lock cause was not established. |
| Retrieval scoring | Exact quote may be split by fixed-size chunking; a valid paraphrase or alternative gold page is not recognized automatically. | Store full top-3 traces and mark exact-hit results conservatively. The audit draft records cases requiring human adjudication; no benchmark numbers were silently changed. |
| Model reproducibility | FastEmbed model name and package versions are recorded, but the downloaded model revision is not pinned. | `starter/requirements.txt` pins package versions; future reruns may vary if model contents at the registry change. |

No provider or quota failure occurred in the successful final runs. API service cost was $0 because embedding and vector search ran locally.

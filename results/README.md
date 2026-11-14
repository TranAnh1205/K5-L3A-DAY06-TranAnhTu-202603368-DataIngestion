# Day 06 retrieval evaluation

The frozen benchmark was run in order: 15 dev questions × A/B/C, strategy selection recorded, then 5 test questions × A/B/C. `dev_traces.json` and `test_traces.json` contain all 3 retrieved chunks per question, including full text, score, metadata, gold evidence, and exact-hit flags. The automatic hit rule is conservative: a single chunk must contain the complete recorded quote and match the gold document and physical PDF page.

`reingest_check.json` records an isolated Qdrant store probe: stable IDs and count after the same two chunks are upserted again, stale-point deletion and payload update after one chunk changes, and section-filter behavior. It uses synthetic vectors and does not measure repeat embedding work on the full corpus.

`full_reingest_check.json` records a repeat run of the real 67-page corpus: A stayed at 484 points, B at 549, and sorted point-ID hashes were identical before and after. The pipeline re-embedded all documents. `model_provenance.json` records the observed local FastEmbed snapshot revision and hashes of ONNX/tokenizer files, while noting that downloads on another machine are not yet pinned to that revision. `audit_review_pack.md` and `../benchmark/gold_review.md` record student confirmation on 2026-11-14; `audit_confirmed.json` links the confirmed scores to the unchanged AI-assisted draft.

| Strategy | Dev Hit@1 | Dev Evidence Hit@3 | Test Hit@1 | Test Evidence Hit@3 | Chunks |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 8/15 | 12/15 | 1/5 | 2/5 | 484 |
| B | 10/15 | 11/15 | 1/5 | 3/5 | 549 |
| C | 10/15 | 11/15 | 1/5 | 4/5 | 549 |

`strategy_selection.json` locks **A** from dev under the predeclared rule: Evidence Hit@3, then Hit@1, then fewer chunks. The better C test score does not retroactively change this choice. Test contains only five questions; these rates do not establish a generally best strategy.

## Five evaluation dimensions

1. **Retrieval accuracy:** See integer counts above and each top-3 trace. Exact-match scoring can mark a partial or differently worded valid passage as a miss; equivalent evidence requires documented review.
2. **Chunk coherence:** The student confirmed the AI-proposed scores on the same 10 source anchors (first 10 eligible PDF pages, character offset 240): A 1.0/2, B 1.8/2, C 1.8/2. This sample emphasizes page beginnings, so its estimate may be biased.
3. **Metadata usefulness:** All 45 test top-3 records have `source`, PDF page, printed page and `section` consistent with the manifest. C's one test filter request returned only Part 2 chunks (1/1 question); A/B intentionally did not apply a filter. `section` helps restrict a query to the requested report part; it is coarse and cannot distinguish subsections within a part.
4. **Grounding quality:** Student-confirmed top-3 evidence scores on the same five test questions are A 1.4/2, B 1.4/2, C 1.6/2. These describe whether retrieval supplied enough evidence to answer, not LLM answer correctness. Per-question scores and reasons are in `audit_draft.json` and the confirmed review pack.
5. **Data strategy impact:** A→B changes fixed windows to sentence groups; the latter improve sampled coherence but use 65 more chunks and score one fewer exact Evidence Hit@3 on dev. B→C changes only query-time metadata filtering; it improves exact test Evidence Hit@3 from 3/5 to 4/5, primarily on `t02`, while dev remains 11/15. Local API cost is $0; see `../starter/results/ingestion_summary.json` and split summaries for elapsed time.

Failure examples: on `t01`, A's gold-page chunk stops mid-list, so the full three-group evidence is missing; B/C retrieve related recovery text but not the list. On `t02`, A/B rank an Overview comparison using the DOU method, while the question asks for DB town rates; C's Part 2 filter brings the correct DB passage into rank 2. On `t05`, A's top chunk cuts off before the non-migrant percentage, whereas B/C retain the full comparison.

`audit_draft.json` was prepared by AI-assisted inspection of trace text, with programmatic metadata checks against the manifest. The student reported checking the PDF and agreeing with all 45 proposed coherence/grounding scores on 2026-11-14; [review pack](audit_review_pack.md) records each confirmed score, and `audit_confirmed.json` records the unchanged summary and draft hash. Third-party figures, extraction artifacts, source duplication, and possible equivalent passages on other pages remain limitations.

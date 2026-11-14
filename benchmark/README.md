# Frozen benchmark (created before retrieval experiments)

`questions.json` contains 20 questions for the World Bank report in `data/manifest.json`: 15 development and 5 holdout test questions. The split was fixed before running any vector search. All questions are in English to match the source language. Each has an expected answer, a physical PDF page number, and an evidence quote checked against the PDF's extracted text. The printed page number is physical page minus 10.

Four questions have a `section` filter, including one test question. Each filter is stated in the question as Part 1 or Part 2; the value comes from the report's section boundaries, not from the gold page supplied to retrieval. Questions without a filter must run without one in configuration C.

Run from the repository root:

```powershell
python benchmark/validate.py
```

The PDF must first be downloaded using `python data/prepare_corpus.py`. Some evidence quotes preserve PDF extraction artifacts (for example a space after a hyphen or a footnote marker) so the validation can check exact source text. Retrieval evaluation should allow a human-confirmed equivalent passage on another legitimate page; record that decision in the trace rather than silently changing this benchmark. Choose strategy parameters using dev only, then evaluate the unchanged test split.

`gold_review.md` provides all 20 question/answer/quote pairs with nearby source text. Trần Anh Tú confirmed on 2026-11-14 that he checked the PDF and agreed with every answer and quote. Automatic validation separately proves the quotes' locations. No benchmark item was changed after test.

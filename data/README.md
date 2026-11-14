# Corpus for Day 06

**Topic:** Poverty, equity and urban inclusion in Viet Nam, using one World Bank report.

**Source:** World Bank (2024), *Viet Nam bi-annual poverty & equity update - June 2024: Towards more inclusive cities*. The PDF and its CC BY 3.0 IGO attribution and third-party-content notice are available at the URL in `manifest.json`.

The 8.3 MB PDF is downloaded locally and ignored by Git. To reproduce the selected corpus from the repository root:

```powershell
python -m pip install pypdf==6.21.4
python data/prepare_corpus.py
```

The script verifies the PDF SHA-256 and writes `manifest.json` with physical and printed page numbers, section labels, and text lengths. Of 92 physical PDF pages, 67 pages contain selected relevant text: 6 overview, 30 Part 1, and 31 Part 2. The manifest lists excluded pages and the counting rule. `section` is taken from the report's own part boundaries and can support a meaningful filter in the later benchmark.

The PDF is in English. Ingestion currently normalizes Unicode and whitespace; some extracted text still contains layout artifacts, footnote markers or incorrect characters. Evidence must be checked against the source pages. Figures and tables may need separate treatment. The source PDF is not committed, and reuse of third-party figures or tables needs separate permission checks.

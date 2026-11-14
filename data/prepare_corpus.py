"""Download the selected public report and record its traceable PDF pages.

Run from the repository root: python data/prepare_corpus.py
Requires pypdf. The source PDF stays local in data/raw/ and is not committed.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data/raw/world_bank_vietnam_poverty_equity_june_2024.pdf"
MANIFEST = ROOT / "data/manifest.json"
URL = "https://documents1.worldbank.org/curated/en/099070224032598476/pdf/P1810941a2c34a0491b71e1f532b48e129f.pdf"
EXPECTED_SHA256 = "5e95b6bcb352fe002e9d4447c6a1e0936a841777e320e5b8e344856829c85ec4"


def normalized_text(page) -> str:
    return re.sub(r"\s+", " ", page.extract_text() or "").strip()


def section_for(physical_page: int) -> str | None:
    if 11 <= physical_page <= 16:
        return "overview"
    if 18 <= physical_page <= 47:
        return "part_1_poverty_equity_update"
    if 55 <= physical_page <= 87 and physical_page not in {72, 78}:
        return "part_2_urban_inclusion"
    return None


def main() -> None:
    PDF.parent.mkdir(parents=True, exist_ok=True)
    if not PDF.exists():
        request = Request(URL, headers={"User-Agent": "student-data-ingestion-lab/1.0"})
        with urlopen(request, timeout=60) as response, PDF.open("wb") as output:
            while block := response.read(1024 * 1024):
                output.write(block)

    actual_hash = hashlib.sha256(PDF.read_bytes()).hexdigest()
    if actual_hash != EXPECTED_SHA256:
        raise ValueError(f"PDF version changed: expected {EXPECTED_SHA256}, got {actual_hash}")

    reader = PdfReader(PDF)
    if len(reader.pages) != 92:
        raise ValueError(f"Expected 92 physical PDF pages, got {len(reader.pages)}")

    pages = []
    for physical_page, page in enumerate(reader.pages, start=1):
        section = section_for(physical_page)
        if section is None:
            continue
        text = normalized_text(page)
        if len(text) < 500:
            raise ValueError(f"Included page {physical_page} has only {len(text)} characters")
        pages.append(
            {
                "page_id": f"pdf-p{physical_page:03d}",
                "physical_page": physical_page,
                "printed_page": physical_page - 10,
                "section": section,
                "normalized_character_count": len(text),
            }
        )

    manifest = {
        "source_id": "worldbank-vnm-poverty-equity-2024-06",
        "title": "Viet Nam bi-annual poverty & equity update - June 2024: Towards more inclusive cities",
        "source_path_or_url": URL,
        "local_path": "data/raw/world_bank_vietnam_poverty_equity_june_2024.pdf",
        "publisher": "World Bank",
        "language": "en",
        "accessed_at": "2026-11-13",
        "snapshot_sha256": actual_hash,
        "license_or_permission": "Creative Commons Attribution 3.0 IGO (CC BY 3.0 IGO); cite World Bank (2024), report title, Washington DC, and license. Check third-party figures/tables separately before redistributing them.",
        "license_url": "https://creativecommons.org/licenses/by/3.0/igo/",
        "physical_page_count": len(reader.pages),
        "counting_rule": "Count only selected physical PDF pages with relevant extractable narrative. Printed page numbers are physical page minus 10. Cover, front matter, blank pages, figure-only pages, annex figures, references and back cover are excluded. No page is duplicated.",
        "excluded_physical_pages": {
            "1-10": "cover, rights, contents and front matter",
            "17": "blank",
            "48-54": "annex figures and Part 2 divider",
            "72, 78": "mostly figures/maps with little narrative",
            "88": "annex figure",
            "89-92": "references, blank page and back cover",
        },
        "included_page_count": len(pages),
        "total_normalized_characters": sum(p["normalized_character_count"] for p in pages),
        "metadata_filter_field": "section",
        "metadata_filter_values": sorted({p["section"] for p in pages}),
        "normalization_for_count": "pypdf extract_text, whitespace collapsed to one space, outer whitespace stripped",
        "pages": pages,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {MANIFEST.relative_to(ROOT)}: {len(pages)} included pages, {manifest['total_normalized_characters']} characters")


if __name__ == "__main__":
    main()

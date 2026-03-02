#!/usr/bin/env python3
"""
Build script for Cesar Galindo's academic website.

Usage:
  python build/build.py            # fetches recent papers from arXiv
  python build/build.py --no-arxiv # skip arXiv fetch (offline mode)

Reads:
  build/papers.json              — publication data and config
  build/template.html            — HTML template for index.html
  build/publications_template.html — HTML template for publications.html

Outputs:
  index.html         — main page (commit this to GitHub)
  publications.html  — full publication list (commit this to GitHub)
"""

import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Paths (all relative to repo root, which is the parent of build/)
# ---------------------------------------------------------------------------
REPO_ROOT             = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_DIR             = os.path.join(REPO_ROOT, "build")
OUTPUT                = os.path.join(REPO_ROOT, "index.html")
PUBLICATIONS_OUTPUT   = os.path.join(REPO_ROOT, "publications.html")
PAPERS_FILE           = os.path.join(BUILD_DIR, "papers.json")
TEMPLATE_FILE         = os.path.join(BUILD_DIR, "template.html")
PUBLICATIONS_TEMPLATE = os.path.join(BUILD_DIR, "publications_template.html")

ARXIV_NS     = "http://www.w3.org/2005/Atom"
ARXIV_EXT_NS = "http://arxiv.org/schemas/atom"


# ---------------------------------------------------------------------------
# arXiv fetching
# ---------------------------------------------------------------------------

def fetch_arxiv(author_id: str) -> bytes:
    # Use the author profile Atom feed — more reliable than the API search
    # and returns all papers for the exact author profile.
    url = f"https://arxiv.org/a/{author_id}.atom"
    print(f"  Fetching: {url}")
    req = urllib.request.Request(
        url, headers={"User-Agent": "AcademicPageBuilder/1.0 (galindo academic site)"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def parse_arxiv(xml_bytes: bytes) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    papers = []
    for entry in root.findall(f"{{{ARXIV_NS}}}entry"):
        id_el = entry.find(f"{{{ARXIV_NS}}}id")
        if id_el is None:
            continue
        # strip version suffix (e.g. 2404.08552v2 → 2404.08552)
        arxiv_id = id_el.text.strip().split("/abs/")[-1].split("v")[0]

        title_el = entry.find(f"{{{ARXIV_NS}}}title")
        title = " ".join(title_el.text.split()) if title_el is not None else "Unknown"

        published_el = entry.find(f"{{{ARXIV_NS}}}published")
        year = int(published_el.text[:4]) if published_el is not None else 0

        authors = [
            a.find(f"{{{ARXIV_NS}}}name").text.strip()
            for a in entry.findall(f"{{{ARXIV_NS}}}author")
            if a.find(f"{{{ARXIV_NS}}}name") is not None
        ]

        jref_el = entry.find(f"{{{ARXIV_EXT_NS}}}journal_ref")
        journal_ref = (
            " ".join(jref_el.text.split())
            if jref_el is not None and jref_el.text
            else None
        )

        doi_el = entry.find(f"{{{ARXIV_EXT_NS}}}doi")
        doi = doi_el.text.strip() if doi_el is not None and doi_el.text else None

        papers.append(
            {
                "arxiv_id": arxiv_id,
                "title": title,
                "year": year,
                "authors": authors,
                "journal_ref": journal_ref,
                "doi": doi,
            }
        )
    return papers


# ---------------------------------------------------------------------------
# HTML generation helpers
# ---------------------------------------------------------------------------

def _esc(text: str) -> str:
    """Minimal HTML escaping."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def arxiv_paper_to_li(paper: dict, num: int = 0) -> str:
    authors_str = ", ".join(paper["authors"])
    title = _esc(paper["title"])
    arxiv_id = paper["arxiv_id"]
    arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"

    if paper.get("journal_ref"):
        source = f"<em>{_esc(paper['journal_ref'])}</em>."
    elif paper.get("doi"):
        source = (
            f'<a href="https://doi.org/{_esc(paper["doi"])}" '
            f'target="_blank" rel="noopener">'
            f'doi:{_esc(paper["doi"])}</a>.'
        )
    else:
        source = f"arXiv:{arxiv_id}."

    num_prefix = f"{num}.&nbsp;" if num else ""
    return (
        f"      <li>\n"
        f"        {num_prefix}{_esc(authors_str)}.\n"
        f'        <a href="{arxiv_url}" target="_blank" rel="noopener">{title}</a>.\n'
        f"        {source}\n"
        f"      </li>"
    )


def selected_pub_to_li(pub: dict) -> str:
    authors = pub["authors"]
    title   = pub["title"]
    year    = pub.get("year", "")
    journal = pub.get("journal", "")
    volume  = pub.get("volume", "")
    number  = pub.get("number", "")
    pages   = pub.get("pages", "")
    doi     = pub.get("doi", "")
    axid    = pub.get("arxiv_id", "")

    # Build journal citation string
    journal_parts = []
    if journal:
        journal_parts.append(f"<em>{_esc(journal)}</em>")
    if volume:
        journal_parts.append(f"<strong>{_esc(volume)}</strong>")
    if year:
        journal_parts.append(f"({year})")
    if number:
        journal_parts.append(f"no. {_esc(number)}")
    if pages:
        journal_parts.append(_esc(pages))
    journal_str = (",".join(journal_parts[:2])        # "Journal vol"
                   + (" " if len(journal_parts) > 2 else "")
                   + (",".join(journal_parts[2:]))    # "(year), no. X, pp"
                   + ".") if journal_parts else ""

    # Primary link: DOI preferred, else arXiv
    link_url = f"https://doi.org/{doi}" if doi else (
               f"https://arxiv.org/abs/{axid}" if axid else "#")

    # arXiv badge
    arxiv_badge = (
        f' [<a href="https://arxiv.org/abs/{axid}" target="_blank" rel="noopener">arXiv</a>]'
        if axid else ""
    )

    return (
        f"      <li>\n"
        f"        {_esc(authors)}.\n"
        f'        <a href="{link_url}" target="_blank" rel="noopener">{_esc(title)}</a>.\n'
        f"        {journal_str}{arxiv_badge}\n"
        f"      </li>"
    )


def build_selected_html(selected: list[dict]) -> str:
    return "\n".join(selected_pub_to_li(p) for p in selected)


def build_recent_html(papers: list[dict], min_year: int) -> str:
    recent = [p for p in papers if p["year"] >= min_year]

    by_year: dict[int, list] = defaultdict(list)
    for p in recent:
        by_year[p["year"]].append(p)

    if not by_year:
        return (
            f'    <p>No papers found from {min_year} onwards in arXiv search. '
            f'<a href="https://arxiv.org/a/galindo_c_1.html" '
            f'target="_blank" rel="noopener">Browse arXiv directly.</a></p>'
        )

    parts = []
    for year in sorted(by_year.keys(), reverse=True):
        items = "\n".join(arxiv_paper_to_li(p) for p in by_year[year])
        parts.append(
            f'    <h3>{year}</h3>\n'
            f'    <ul class="pub-list">\n'
            f'{items}\n'
            f'    </ul>'
        )
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Publications page helpers
# ---------------------------------------------------------------------------

def pub_to_li(pub: dict, num: int = 0) -> str:
    """Generate an <li> for a published paper with reverse number and MR badge."""
    authors = pub.get("authors", "")
    title   = pub.get("title", "")
    year    = pub.get("year", "")
    journal = pub.get("journal", "")
    volume  = pub.get("volume", "") or ""
    number  = pub.get("number", "") or ""
    pages   = pub.get("pages", "") or ""
    doi     = pub.get("doi", "") or ""
    axid    = pub.get("arxiv_id", "") or ""
    mr      = pub.get("mr", "") or ""

    # Build journal citation string (same logic as selected_pub_to_li)
    journal_parts = []
    if journal:
        journal_parts.append(f"<em>{_esc(journal)}</em>")
    if volume:
        journal_parts.append(f"<strong>{_esc(str(volume))}</strong>")
    if year:
        journal_parts.append(f"({year})")
    if number:
        journal_parts.append(f"no. {_esc(str(number))}")
    if pages:
        journal_parts.append(_esc(str(pages)))
    journal_str = (",".join(journal_parts[:2])
                   + (" " if len(journal_parts) > 2 else "")
                   + (",".join(journal_parts[2:]))
                   + ".") if journal_parts else ""

    # Primary title link: DOI > arXiv > MR
    if doi:
        title_url = f"https://doi.org/{doi}"
    elif axid:
        title_url = f"https://arxiv.org/abs/{axid}"
    elif mr:
        title_url = f"https://mathscinet.ams.org/mathscinet-getitem?mr={mr}"
    else:
        title_url = "#"

    # Badges
    badges = []
    if mr:
        badges.append(
            f'[<a href="https://mathscinet.ams.org/mathscinet-getitem?mr={mr}" '
            f'target="_blank" rel="noopener">MR{mr}</a>]'
        )
    if axid:
        badges.append(
            f'[<a href="https://arxiv.org/abs/{axid}" '
            f'target="_blank" rel="noopener">arXiv</a>]'
        )
    badges_str = " ".join(badges)

    num_prefix = f"{num}.&nbsp;" if num else ""
    return (
        f"      <li>\n"
        f"        {num_prefix}{_esc(authors)}.\n"
        f'        <a href="{title_url}" target="_blank" rel="noopener">{_esc(title)}</a>.\n'
        f"        {journal_str} {badges_str}\n"
        f"      </li>"
    )


def build_all_publications_html(all_pubs: list[dict]) -> str:
    """Build publications HTML grouped by year, newest first, with reverse numbering."""
    by_year: dict[int, list] = defaultdict(list)
    for p in all_pubs:
        by_year[p["year"]].append(p)

    total = len(all_pubs)
    counter = total   # starts at total, decrements to 1

    parts = []
    for year in sorted(by_year.keys(), reverse=True):
        items_html = []
        for p in by_year[year]:
            items_html.append(pub_to_li(p, num=counter))
            counter -= 1
        parts.append(
            f'    <h3>{year}</h3>\n'
            f'    <ul class="pub-list">\n'
            + "\n".join(items_html) + "\n"
            f'    </ul>'
        )
    return "\n\n".join(parts)


def build_preprints_html(arxiv_papers: list[dict], all_pubs: list[dict], min_year: int) -> str:
    """Build HTML for arXiv preprints not yet in all_publications."""
    known_ids = {p["arxiv_id"] for p in all_pubs if p.get("arxiv_id")}

    # Preprints: recent arXiv papers whose ID is not in the published list
    preprints = [
        p for p in arxiv_papers
        if p["arxiv_id"] not in known_ids and p["year"] >= min_year
    ]
    # Sort newest first (arXiv IDs sort lexicographically in date order)
    preprints.sort(key=lambda p: p["arxiv_id"], reverse=True)

    if not preprints:
        return (
            f'    <p>No preprints found from {min_year} onwards. '
            f'<a href="https://arxiv.org/a/galindo_c_1.html" '
            f'target="_blank" rel="noopener">Browse arXiv directly.</a></p>'
        )

    n = len(preprints)
    items = "\n".join(arxiv_paper_to_li(p, num=n - i) for i, p in enumerate(preprints))
    return f'    <ul class="pub-list">\n{items}\n    </ul>'


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    no_arxiv = "--no-arxiv" in sys.argv

    # --- load config ---------------------------------------------------------
    with open(PAPERS_FILE, encoding="utf-8") as f:
        data = json.load(f)

    all_pubs     = data.get("all_publications", [])
    arxiv_author = data.get("arxiv_author", "galindo_c_1")
    override_min = data.get("recent_papers_min_year")   # null → rolling window

    current_year = datetime.now(timezone.utc).year
    min_year     = int(override_min) if override_min else current_year - 2
    last_updated = datetime.now(timezone.utc).strftime("%B %Y")

    # --- fetch arXiv ---------------------------------------------------------
    if no_arxiv:
        print("Skipping arXiv fetch (--no-arxiv).")
        all_arxiv = []
    else:
        print("Fetching papers from arXiv...")
        try:
            xml_bytes = fetch_arxiv(arxiv_author)
            all_arxiv = parse_arxiv(xml_bytes)
            print(f"  Fetched {len(all_arxiv)} papers from arXiv.")
        except Exception as exc:
            print(f"  WARNING: arXiv fetch failed: {exc}", file=sys.stderr)
            all_arxiv = []

    # --- build index.html ----------------------------------------------------
    print("Building index.html...")
    with open(TEMPLATE_FILE, encoding="utf-8") as f:
        template = f.read()

    index_output = template.replace("__LAST_UPDATED__", last_updated)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(index_output)
    print(f"  Done → {OUTPUT}")

    # --- build publications.html ---------------------------------------------
    print("Building publications.html...")
    with open(PUBLICATIONS_TEMPLATE, encoding="utf-8") as f:
        pub_template = f.read()

    if all_arxiv:
        preprints_html = build_preprints_html(all_arxiv, all_pubs, min_year)
        n_preprints = len([
            p for p in all_arxiv
            if p["arxiv_id"] not in {q["arxiv_id"] for q in all_pubs if q.get("arxiv_id")}
            and p["year"] >= min_year
        ])
        print(f"  Found {n_preprints} preprints from {min_year} onwards.")
    else:
        preprints_html = (
            '    <p><em>Preprints not loaded (offline mode). '
            '<a href="https://arxiv.org/a/galindo_c_1.html" '
            'target="_blank" rel="noopener">See arXiv</a>.</em></p>'
        )

    publications_html = build_all_publications_html(all_pubs)
    print(f"  Built list of {len(all_pubs)} published papers.")

    pub_output = (
        pub_template
        .replace("__PREPRINTS__",    preprints_html)
        .replace("__PUBLICATIONS__", publications_html)
        .replace("__LAST_UPDATED__", last_updated)
    )

    with open(PUBLICATIONS_OUTPUT, "w", encoding="utf-8") as f:
        f.write(pub_output)
    print(f"  Done → {PUBLICATIONS_OUTPUT}")


if __name__ == "__main__":
    main()

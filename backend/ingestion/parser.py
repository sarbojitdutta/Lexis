
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import re
import json
import pdfplumber
from typing import Optional

from config import DATA_PROCESSED, DATA_RAW


# ─────────────────────────────────────────────
# Legal marker patterns
# ─────────────────────────────────────────────

PART_PATTERN      = re.compile(r'^\s*PART\s+([IVXLC\d]+)\s*[—–:.]?\s*(.{0,60})$', re.MULTILINE)
CHAPTER_PATTERN   = re.compile(r'^\s*CHAPTER\s+([IVXLC\d]+)\s*[—–:.]?\s*(.{0,60})$', re.MULTILINE | re.IGNORECASE)

PROVISO_PATTERN   = re.compile(r'\bProvided\s+that\b', re.IGNORECASE)
EXCEPTION_PATTERN = re.compile(r'\bNotwithstanding\b|\bSubject\s+to\b', re.IGNORECASE)
DEFINITION_PATTERN= re.compile(r'\bmeans\b|\bshall\s+mean\b|\bincludes\b', re.IGNORECASE)
AMENDMENT_PATTERN = re.compile(r'\bsubstituted\s+by\b|\binserted\s+by\b|\bomitted\s+by\b', re.IGNORECASE)
CLAUSE_PATTERN    = re.compile(r'\((\d+)\)\s')
CROSS_REF_PATTERN = re.compile(r'\bsection\s+(\d+[A-Z]?)\b|\barticle\s+(\d+[A-Z]?)\b', re.IGNORECASE)


# ─────────────────────────────────────────────
# Step 1 — Extract raw text from PDF pages
# ─────────────────────────────────────────────

def _extract_pages(pdf_path: Path) -> list[str]:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=2, y_tolerance=2)
            if text:
                pages.append(text)
    return pages


# ─────────────────────────────────────────────
# Step 2 — Clean raw text
# ─────────────────────────────────────────────

def _clean_text(text: str) -> str:
    # Remove standalone page numbers on their own line
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)

    # Remove common Indian legal PDF headers/footers
    text = re.sub(r'THE\s+GAZETTE\s+OF\s+INDIA.*?\n', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Ministry\s+of\s+Law.*?\n',         '', text, flags=re.IGNORECASE)
    text = re.sub(r'www\.indiacode\.nic\.in.*?\n',      '', text, flags=re.IGNORECASE)
    text = re.sub(r'www\.legislative\.gov\.in.*?\n',    '', text, flags=re.IGNORECASE)

    # Fix hyphenated line breaks (PDF word wrap artifact)
    text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)

    # Collapse excessive blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Remove non-printable characters — preserve em dash \u2014
    text = re.sub(r'[^\x09\x0A\x0D\x20-\x7E\u00A0-\uFFFF]', '', text)

    return text.strip()


# ─────────────────────────────────────────────
# Step 3 — Skip table of contents, find actual content
# ─────────────────────────────────────────────

def _find_content_start(text: str) -> int:
    """
    Indian legal PDFs always have a table of contents
    before the actual act text. The real content starts
    at PRELIMINARY or PREAMBLE followed by section 1.

    We find the LAST occurrence of PRELIMINARY or PREAMBLE
    because the TOC also contains these words — we want
    where the actual text begins, not the TOC mention.
    """
    # Look for the pattern: PRELIMINARY or PREAMBLE followed
    # shortly by "1." which is section 1 starting
    matches = list(re.finditer(
        r'(PRELIMINARY|PREAMBLE)[^\n]*\n',
        text
    ))

    if not matches:
        # No preliminary found — start from beginning
        return 0

    # Take the last match — this is where actual content begins
    # (earlier matches are in the table of contents)
    return matches[-1].start()


# ─────────────────────────────────────────────
# Step 4 — Detect Part / Chapter context
# ─────────────────────────────────────────────

def _get_structural_context(text: str) -> tuple[list, list]:
    parts = [
        (m.start(), m.group(1), m.group(2).strip())
        for m in PART_PATTERN.finditer(text)
    ]
    chapters = [
        (m.start(), m.group(1), m.group(2).strip())
        for m in CHAPTER_PATTERN.finditer(text)
    ]
    return parts, chapters


def _context_at_position(position: int, positions: list) -> Optional[str]:
    result = None
    for pos, num, name in positions:
        if pos < position:
            result = f"{num} — {name}" if name else num
        else:
            break
    return result


# ─────────────────────────────────────────────
# Step 5 — Split text into section chunks
# ─────────────────────────────────────────────

def _split_sections(text: str, source: str) -> list[dict]:
    """
    Match section headings in this format used by Indian Contract Act:
        1. Short title.\u2014This Act may be called...
        19A. Power to set aside contract...\u2014When consent...

    \u2014 is the em dash character — confirmed from raw PDF output.
    """

    # Primary pattern — covers standard sections and inserted sections (19A, 66A etc.)
    # Matches: number + optional letters + dot + space + title text + dot + em dash
    primary = re.compile(
        r'^\s*(\d+[A-Z]{0,2})\.\s*(.{3,80}?)\.\u2014',
        re.MULTILINE
    )

    # Fallback pattern — title without trailing dot before em dash
    # Matches: 3.Communication, acceptance...\u2014
    fallback = re.compile(
        r'^\s*(\d+[A-Z]{0,2})\.\s*(.{3,80}?)\u2014',
        re.MULTILINE
    )

    matches = list(primary.finditer(text))

    # If primary found very few, try fallback
    if len(matches) < 5:
        matches = list(fallback.finditer(text))

    # Sort by position in case patterns overlap
    matches = sorted(matches, key=lambda m: m.start())

    parts, chapters = _get_structural_context(text)

    if not matches:
        print(f"  Warning: no section headings detected in '{source}'.")
        return [_build_chunk(
            section_id="1", title="Full Document",
            body=text, source=source,
            part=None, chapter=None
        )]

    print(f"  Found {len(matches)} section headings")

    chunks = []
    for i, match in enumerate(matches):
        start      = match.start()
        end        = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body       = text[start:end].strip()
        section_id = match.group(1).strip()
        title      = match.group(2).strip().strip('"').strip("'")

        # Skip very short fragments — likely TOC leftovers
        if len(body.split()) < 15:
            continue

        # Skip pure [Repealed.] sections — no useful content
        if re.search(r'^\s*\d+[A-Z]?\.\s*\[Repealed', body, re.IGNORECASE):
            continue

        part    = _context_at_position(start, parts)
        chapter = _context_at_position(start, chapters)

        chunks.append(_build_chunk(
            section_id = section_id,
            title      = title,
            body       = body,
            source     = source,
            part       = f"Part {part}"       if part    else None,
            chapter    = f"Chapter {chapter}" if chapter else None
        ))

    return chunks


# ─────────────────────────────────────────────
# Step 6 — Build chunk dict with metadata
# ─────────────────────────────────────────────

def _extract_cross_references(text: str) -> list[str]:
    refs = set()
    for match in CROSS_REF_PATTERN.finditer(text):
        ref = match.group(1) or match.group(2)
        if ref:
            refs.add(ref.strip())
    return sorted(refs)


def _build_chunk(section_id: str, title: str, body: str,
                 source: str, part: Optional[str],
                 chapter: Optional[str]) -> dict:
    return {
        "section_id"      : section_id,
        "title"           : title,
        "text"            : body,
        "source"          : source,
        "part"            : part,
        "chapter"         : chapter,
        "word_count"      : len(body.split()),
        "has_proviso"     : bool(PROVISO_PATTERN.search(body)),
        "has_exception"   : bool(EXCEPTION_PATTERN.search(body)),
        "has_definition"  : bool(DEFINITION_PATTERN.search(body)),
        "has_amendment"   : bool(AMENDMENT_PATTERN.search(body)),
        "has_sub_clauses" : bool(CLAUSE_PATTERN.search(body)),
        "cross_references": _extract_cross_references(body),
    }


# ─────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────

def parse_document(file_path: str | Path) -> list[dict]:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if path.suffix.lower() != '.pdf':
        raise ValueError(f"Only PDF files supported. Got: {path.suffix}")

    print(f"Parsing '{path.name}'...")

    pages     = _extract_pages(path)
    full_text = "\n".join(pages)
    full_text = _clean_text(full_text)

    # Skip table of contents — find where actual content begins
    content_start = _find_content_start(full_text)
    content_text  = full_text[content_start:]

    print(f"  Content starts at character {content_start} "
          f"(skipped {content_start} chars of TOC)")

    chunks = _split_sections(content_text, source=path.name)

    # Save to data/processed/
    out_path = DATA_PROCESSED / (path.stem + ".json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    print(f"Done — {len(chunks)} sections saved to '{out_path}'")
    return chunks


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    raw_dir   = DATA_RAW
    pdf_files = list(raw_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in '{raw_dir}'.")
        sys.exit(0)

    print(f"Found {len(pdf_files)} PDF(s) in '{raw_dir}':\n")
    for f in pdf_files:
        print(f"  - {f.name}")
    print()

    all_chunks = []
    for pdf_path in pdf_files:
        chunks = parse_document(pdf_path)
        all_chunks.extend(chunks)

    print(f"\nTotal sections parsed: {len(all_chunks)}")

    if all_chunks:
        print(f"\n--- First 3 chunks ---\n")
        for chunk in all_chunks[:3]:
            print(f"  section_id  : {chunk['section_id']}")
            print(f"  title       : {chunk['title']}")
            print(f"  chapter     : {chunk['chapter']}")
            print(f"  words       : {chunk['word_count']}")
            print(f"  cross_refs  : {chunk['cross_references']}")
            print(f"  text preview: {chunk['text'][:100]}...")
            print()
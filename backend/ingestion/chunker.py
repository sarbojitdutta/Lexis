import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import json
import re
from typing import Optional
from config import DATA_PROCESSED

MAX_WORDS=180
OVERLAP_WORDS=30

def _split_into_words(text: str) -> list[str]:
    return text.split()

def _words_to_text(words: list[str]) -> str:
    return ' '.join(words)

def _chunk_text(text: str, max_words: int, overlap_words: int) -> list[str]:
    """
    Split a long text into overlapping word-window chunks.
    Each chunk is at most max_words long.
    Consecutive chunks share `overlap` words for context continuity.

    Example with max_words=5, overlap=2:
    Text : "A B C D E F G H I J"
    Chunk 1 : "A B C D E"
    Chunk 2 : "D E F G H"   ← starts 2 words back (overlap)
    Chunk 3 : "G H I J"
    """
    words = _split_into_words(text)
    chunks = []
    start = 0

    while start < len(words):
        end = min(start + max_words, len(words))
        chunk_texts = _words_to_text(words[start:end])
        chunks.append(chunk_texts)

        if end == len(words):
            break

        start = end - overlap_words  # Move back by overlap for the next chunk

    return chunks

def _split_sentences(text: str) -> list[str]:
    """
    Split text into sentences using punctuation.
    Legal text uses full stops, semicolons, and provisos
    as natural sentence boundaries.
    """

    sentences = re.split(r'(?<=[.;])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def _chunk_by_sentences(text: str, max_words: int, overlap_words: int) -> list[str]:
    """
    Smarter chunking — fills each chunk sentence by sentence
    until it would exceed max_words, then starts a new chunk.
    Overlap is achieved by carrying the last sentence(s) forward.

    This avoids cutting a chunk mid-sentence which would produce
    incomplete legal statements like "Provided that the person shall"
    with no continuation.
    """

    sentences = _split_sentences(text)
    chunks = []
    current = []
    current_word_count = 0

    for sentence in sentences:
        sentence_words = len(sentence.split())

        if current_word_count + sentence_words > max_words and current:
            chunks.append(" ".join(current))

            overlap_buffer = []  
            overlap_count = 0
            for prev_sentence in reversed(current):
                prev_words = len(prev_sentence.split())
                if overlap_count + prev_words <= overlap_words:
                    overlap_buffer.insert(0, prev_sentence)
                    overlap_count += prev_words
                else:
                    break

            current            = overlap_buffer
            current_word_count = overlap_count

        current.append(sentence)
        current_word_count += sentence_words

    if current:
        chunks.append(" ".join(current))

    return chunks

def _build_sub_chunk(text: str, parent: dict, chunk_index: int, total_chunks: int) -> dict:
    """
    Each sub-chunk inherits all metadata from its parent section
    and adds its own positional info so we can always trace back
    to the original section.
    """
    return {
        # Identity
        "chunk_id"      : f"{parent['source']}__s{parent['section_id']}__c{chunk_index}",
        "section_id"    : parent["section_id"],
        "chunk_index"   : chunk_index,
        "total_chunks"  : total_chunks,

        # Content
        "text"          : text,
        "word_count"    : len(text.split()),

        # Inherited section metadata
        "title"         : parent["title"],
        "source"        : parent["source"],
        "part"          : parent["part"],
        "chapter"       : parent["chapter"],

        # Inherited legal markers — kept on every sub-chunk
        # so retrieval can filter by these flags
        "has_proviso"      : parent["has_proviso"],
        "has_exception"    : parent["has_exception"],
        "has_definition"   : parent["has_definition"],
        "has_amendment"    : parent["has_amendment"],
        "has_sub_clauses"  : parent["has_sub_clauses"],
        "cross_references" : parent["cross_references"],
    }

def chunk_section(section: dict, max_words: int   = MAX_WORDS, overlap: int    = OVERLAP_WORDS) -> list[dict]:
    """
    Takes one section dict from parser.py output and returns
    a list of sub-chunk dicts ready for embedding.

    If the section is short enough it comes back as a single chunk.
    If it is long it gets split into overlapping sub-chunks.
    """
    text       = section["text"]
    word_count = section["word_count"]

    # Short section — no splitting needed, return as-is
    if word_count <= max_words:
        return [_build_sub_chunk(
            text=text,
            parent=section,
            chunk_index=0,
            total_chunks=1
        )]

    # Long section — split by sentences with overlap
    raw_chunks = _chunk_by_sentences(text, max_words, overlap)

    # Safety fallback — if sentence splitter produced nothing
    # (very unlikely but defensive), fall back to word-window split
    if not raw_chunks:
        raw_chunks = _chunk_text(text, max_words, overlap)

    return [
        _build_sub_chunk(
            text=chunk_text,
            parent=section,
            chunk_index=i,
            total_chunks=len(raw_chunks)
        )
        for i, chunk_text in enumerate(raw_chunks)
    ]

def chunk_document(sections: list[dict]) -> list[dict]:
    """
    Takes the full list of sections from parse_document()
    and returns a flat list of all sub-chunks across all sections.
    """
    all_chunks = []

    for section in sections:
        sub_chunks = chunk_section(section)
        all_chunks.extend(sub_chunks)

    return all_chunks

def chunk_from_file(json_path: Path) -> list[dict]:
    """
    Load a processed JSON file produced by parser.py
    and return all sub-chunks.
    """
    with open(json_path, encoding="utf-8") as f:
        sections = json.load(f)

    chunks = chunk_document(sections)

    print(f"  {json_path.name}: {len(sections)} sections "
          f"→ {len(chunks)} chunks")
    return chunks

if __name__ == "__main__":
    processed_dir = DATA_PROCESSED
    json_files = list(processed_dir.glob("*.json"))

    if not json_files:
        print(f"No JSON files found in {processed_dir}.")
        print("Run parser.py first")
        sys.exit(0)

    print(f"Found {len(json_files)} processed file(s):\n")

    all_chunks = []
    for json_path in json_files:
        chunks = chunk_from_file(json_path)
        all_chunks.extend(chunks)

    print(f"\nTotal chunks across all documents : {len(all_chunks)}")
    



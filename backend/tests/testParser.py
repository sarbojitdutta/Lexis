import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pytest
from ingestion.parser import _clean_text, _extract_cross_references

class TestCleanText:

    def test_remove_page_numbers(self):
        text = "Some legal text\n42\nMore text"
        result = _clean_text(text)
        assert "\n42\n" not in result

    def test_fixes_hyphenated_line_breaks(self):
        text = "competent\nto contract"
        result = _clean_text(text)
        text2  = "compe-\ntent"
        result2 = _clean_text(text2)

        assert "competent" in result
        assert "competent" in result2

    def test_removes_gazette_header(self):
        text   = "THE GAZETTE OF INDIA EXTRA\nSome content"
        result = _clean_text(text)
        assert "GAZETTE" not in result

    def test_preserves_em_dash(self):
        text   = "10. Short title\u2014This Act"
        result = _clean_text(text)
        assert "\u2014" in result

    def test_collapses_blank_lines(self):
        text   = "Line 1\n\n\n\n\nLine 2"
        result = _clean_text(text)
        assert "\n\n\n" not in result

class TestCrossReference:
    def test_extracts_section_references(self):
        text = "as defined in section 15 and section 16"
        refs = _extract_cross_references(text)
        assert "15" in refs
        assert "16" in refs

    def test_extracts_article_references(self):
        text = "subject to article 21 of the Constitution"
        refs = _extract_cross_references(text)
        assert "21" in refs

    def test_no_duplicates(self):
        text = "section 15 and section 15 again"
        refs = _extract_cross_references(text)
        assert refs.count("15") == 1

    def test_empty_text(self):
        refs = _extract_cross_references("")
        assert refs == []

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from retrieval.vector_search import search, get_section_ids
from retrieval.merger        import merge, build_context, build_citations


class TestVectorSearch:

    def test_search_returns_list(self):
        results = search("what is a contract", k=3)
        assert isinstance(results, list)

    def test_search_returns_correct_count(self):
        results = search("free consent", k=4)
        assert len(results) <= 4

    def test_search_results_have_required_fields(self):
        results = search("breach of contract", k=2)
        for r in results:
            assert "text"       in r
            assert "section_id" in r
            assert "score"      in r
            assert "title"      in r

    def test_search_scores_between_zero_and_one(self):
        results = search("minor contract", k=3)
        for r in results:
            assert 0.0 <= r["score"] <= 1.0

    def test_search_scores_descending(self):
        results = search("coercion", k=5)
        scores  = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_get_section_ids_returns_strings(self):
        ids = get_section_ids("free consent", k=3)
        assert all(isinstance(i, str) for i in ids)

    def test_get_section_ids_no_duplicates(self):
        ids = get_section_ids("contract agreement", k=5)
        assert len(ids) == len(set(ids))

    def test_legal_query_finds_relevant_section(self):
        results = search("who can enter into a contract", k=5)
        section_ids = [r["section_id"] for r in results]
        # Section 11 is about competence to contract
        # should appear in top results
        assert "11" in section_ids


class TestMerger:

    def test_merge_returns_list(self):
        results = merge("what is free consent")
        assert isinstance(results, list)

    def test_merge_results_have_required_fields(self):
        results = merge("breach of contract")
        for r in results:
            assert "text"        in r
            assert "section_id"  in r
            assert "score"       in r
            assert "source_type" in r

    def test_build_context_returns_string(self):
        context, used = build_context("what is a contract")
        assert isinstance(context, str)
        assert len(context) > 0

    def test_build_context_within_word_limit(self):
        from config import MAX_CONTEXT
        context, used = build_context("free consent coercion")
        word_count    = len(context.split())
        assert word_count <= MAX_CONTEXT + 50  # small buffer

    def test_build_citations_filters_empty(self):
        results = [
            {"section_id": "10", "title": "Test",  "source": "test.pdf",
             "source_type": "vector", "score": 0.9},
            {"section_id": "11", "title": "",       "source": "",
             "source_type": "graph_traversal", "score": 0.75},
        ]
        citations = build_citations(results)
        # Empty title and source should be filtered
        assert all(
            c["title"] or c["source"]
            for c in citations
        )

    def test_no_duplicate_citations(self):
        context, used = build_context("contract agreement consent")
        citations     = build_citations(used)
        section_ids   = [c["section_id"] for c in citations]
        assert len(section_ids) == len(set(section_ids))
from retrieval.vector_search import search

GOLD_STANDARD = [
    {
        "question"        : "Who is competent to contract",
        "expected_sections": ["11"],
        "must_contain"    : ["age of majority", "sound mind"],
        "must_not_contain": ["void", "voidable"],
    },
    {
        "question"        : "What is free consent",
        "expected_sections": ["14"],
        "must_contain"    : ["coercion", "fraud", "misrepresentation"],
        "must_not_contain": [],
    },
    {
        "question"        : "What makes an agreement void",
        "expected_sections": ["2", "10"],
        "must_contain"    : ["lawful", "consideration"],
        "must_not_contain": [],
    },
    {
        "question"        : "What is coercion",
        "expected_sections": ["15"],
        "must_contain"    : ["Indian Penal Code"],
        "must_not_contain": [],
    },
]

class TestRAGQuality:
    def finds_correct_sections(self):
        for case in GOLD_STANDARD:
            results     = search(case["question"], k=5)
            section_ids = [r["section_id"] for r in results]

            for expected in case["expected_sections"]:
                assert expected in section_ids, (
                    f"Expected section {expected} in results for "
                    f"'{case['question']}' but got {section_ids}"
                )
    def contains_required_items(self, client):
        for case in GOLD_STANDARD:
            response = client.post(
                "/api/query",
                json={"question": case["question"]}
            )
            answer = response.json()["answer"].lower()

            for term in case["must_contain"]:
                assert term.lower() in answer, (
                    f"Expected '{term}' in answer for "
                    f"'{case['question']}'"
                )
    def citations_include_correct_sections(self, client):
        for case in GOLD_STANDARD:
            response  = client.post(
                "/api/query",
                json={"question": case["question"]}
            )
            citations = response.json()["citations"]
            cited_ids = [c["section_id"] for c in citations]

            for expected in case["expected_sections"]:
                assert expected in cited_ids, (
                    f"Expected citation for section {expected} "
                    f"in answer for '{case['question']}'"
                )

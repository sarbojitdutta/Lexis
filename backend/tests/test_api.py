
class TestHealthEndPoint:
    def test_health_returns_200(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_has_required_fields(self, client):
        data = client.get("/api/health").json()
        assert "status" in data
        assert "vector_index" in  data
        assert "graph_db" in data
        assert "total_vectors" in data

    def test_query_answer_is_string(self, client):
        response = client.post(
            "/api/query",
            json={"question": "What is free consent?"}
        )
        assert isinstance(response.json()["answer"], str)

    def test_query_answer_not_empty(self, client):
        response = client.post(
            "/api/query",
            json={"question": "What is a void agreement?"}
        )
        assert len(response.json()["answer"]) > 50

    def test_query_rejects_short_question(self, client):
        response = client.post(
            "/api/query",
            json={"question": "hi"}
        )
        # min_length=5 in schema
        assert response.status_code == 422

    def test_query_rejects_empty_question(self, client):
        response = client.post(
            "/api/query",
            json={"question": ""}
        )
        assert response.status_code == 422

    def test_query_citations_have_section_ids(self, client):
        response = client.post(
            "/api/query",
            json={"question": "Can a minor enter into a contract?"}
        )
        citations = response.json()["citations"]
        for c in citations:
            assert "section_id" in c
            assert c["section_id"] != ""

class TestDocumentsEndpoint:

    def test_documents_returns_200(self, client):
        response = client.get("/api/documents")
        assert response.status_code == 200

    def test_documents_has_required_fields(self, client):
        data = client.get("/api/documents").json()
        assert "documents"    in data
        assert "total_chunks" in data

class TestGraphEndpoint:

    def test_graph_stats_returns_200(self, client):
        response = client.get("/api/graph/stats")
        assert response.status_code == 200

    def test_graph_node_returns_200(self, client):
        response = client.get("/api/graph/node/10")
        assert response.status_code == 200

    def test_graph_node_has_section_id(self, client):
        data = client.get("/api/graph/node/14").json()
        assert data["section_id"] == "14"


    




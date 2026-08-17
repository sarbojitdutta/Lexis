import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from pydantic import BaseModel, Field, ConfigDict
from typing  import Optional

# Request schemas

class QueryRequest(BaseModel):
    """
    Request body for POST /api/query
    The main endpoint — user asks a legal question
    """
    question : str = Field(
        ...,
        min_length  = 5,
        max_length  = 500,
        description = "Legal question to ask"
    )
    k_vector : Optional[int] = Field(
        default     = 4,
        ge          = 1,
        le          = 10,
        description = "Number of vector search results"
    )
    k_graph  : Optional[int] = Field(
        default     = 6,
        ge          = 1,
        le          = 20,
        description = "Number of graph search results"
    )

    model_config = ConfigDict(
        json_schema_extra = {
                    "example": {
                        "question": "Can a minor enter into a contract?",
                        "k_vector": 4,
                        "k_graph" : 6,
                    }
                }
    )
        


class IngestRequest(BaseModel):
    """
    Request body for POST /api/ingest
    Trigger ingestion of a new document
    """
    filename : str = Field(
        ...,
        description = "PDF filename inside data/raw/ folder"
    )

    model_config = ConfigDict(
        json_schema_extra = {
                    "example": {
                        "filename": "indian_contract_act.pdf"
                    }
                }
    )
        



# Response schemas

class Citation(BaseModel):
    """
    A single source citation returned with the answer.
    Frontend uses this to show source references.
    """
    section_id  : str
    title       : str
    source      : str
    source_type : str
    score       : float


class QueryResponse(BaseModel):
    """
    Response body for POST /api/query
    """
    question  : str
    answer    : str
    citations : list[Citation]
    context_used : int = Field(
        description = "Number of context chunks used"
    )

    model_config = ConfigDict(
        json_schema_extra = {
                    "example": {
                        "question" : "Can a minor enter into a contract?",
                        "answer"   : "According to Section 11...",
                        "citations": [
                            {
                                "section_id" : "11",
                                "title"      : "Who are competent to contract",
                                "source"     : "A187209.pdf",
                                "source_type": "vector",
                                "score"      : 0.92
                            }
                        ],
                        "context_used": 6
                    }
                }
        
    )
        

class DocumentInfo(BaseModel):
    """
    Info about a single ingested document.
    """
    filename    : str
    section_count: int
    chunk_count : int
    status      : str


class DocumentListResponse(BaseModel):
    """
    Response for GET /api/documents
    """
    documents   : list[DocumentInfo]
    total_chunks: int


class IngestResponse(BaseModel):
    """
    Response for POST /api/ingest
    """
    filename    : str
    sections    : int
    chunks      : int
    graph_nodes : int
    graph_edges : int
    status      : str
    message     : str


class GraphNode(BaseModel):
    """
    A single node in the SAT graph.
    """
    node_id    : str
    type       : str
    text       : str
    section_id : str


class GraphEdge(BaseModel):
    """
    A single edge in the SAT graph.
    """
    src      : str
    dst      : str
    relation : str


class GraphResponse(BaseModel):
    """
    Response for GET /api/graph/node/:id
    Returns a node and all its neighbours
    for frontend graph visualisation.
    """
    section_id  : str
    node        : Optional[GraphNode]
    neighbours  : list[GraphNode]
    edges       : list[GraphEdge]


class HealthResponse(BaseModel):
    """
    Response for GET /api/health
    """
    status      : str
    project     : str
    llm_status  : str
    llm_model   : str
    vector_index: str
    graph_db    : str
    total_vectors: int
    total_nodes : int
    total_edges : int


class ErrorResponse(BaseModel):
    """
    Standard error response shape
    """
    error   : str
    detail  : Optional[str] = None
    status_code: int
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from api.main import app

@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c: #FastAPI Testclient connected to app once for whole test session.
        yield c

@pytest.fixture(scope="session")
def sample_section():

    return [
        {
            "section_id"      : "10",
            "title"           : "What agreements are contracts",
            "text"            : "10. What agreements are contracts — All agreements are contracts if they are made by the free consent of parties competent to contract, for a lawful consideration and with a lawful object.",
            "source"          : "test.pdf",
            "part"            : None,
            "chapter"         : None,
            "word_count"      : 42,
            "has_proviso"     : False,
            "has_exception"   : False,
            "has_definition"  : False,
            "has_amendment"   : False,
            "has_sub_clauses" : False,
            "cross_references": ["11", "14"],
        },
        {
            "section_id"      : "11",
            "title"           : "Who are competent to contract",
            "text"            : "11. Who are competent to contract — Every person is competent to contract who is of the age of majority according to the law to which he is subject, and who is of sound mind.",
            "source"          : "test.pdf",
            "part"            : None,
            "chapter"         : None,
            "word_count"      : 38,
            "has_proviso"     : False,
            "has_exception"   : False,
            "has_definition"  : False,
            "has_amendment"   : False,
            "has_sub_clauses" : False,
            "cross_references": [],
        }
    ]

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
import pytest
import numpy as np
from ingestion.embedder import embed_chunks

class TestEmbedder:
    def test_embed_returns_numpy_array(self, sample_section):
        embeddings = embed_chunks(sample_section)
        assert isinstance(embeddings, np.ndarray)

    def test_embed_correct_dimension(self, sample_section):
        embeddings = embed_chunks(sample_section)
        # all-MiniLM-L6-v2 produces 384 dimensions
        assert embeddings.shape[1] == 384

    def test_embed_correct_count(self, sample_section):
        embeddings = embed_chunks(sample_section)
        assert embeddings.shape[0] == len(sample_section)

    def test_embeddings_are_normalized(self, sample_section):
        embeddings = embed_chunks(sample_section)
        # Normalized vectors have magnitude = 1.0
        magnitudes = np.linalg.norm(embeddings, axis=1)
        assert np.allclose(magnitudes, 1.0, atol=1e-5)

    def test_handles_empty_text(self):
        chunks = [{"text": "", "section_id": "1"}]
        # Should not crash — empty text gets replaced
        embeddings = embed_chunks(chunks)
        assert embeddings is not None

    def test_different_texts_produce_different_embeddings(self):
        chunks = [
            {"text": "contract law and agreements", "section_id": "1"},
            {"text": "criminal law and punishment",  "section_id": "2"},
        ]
        embeddings = embed_chunks(chunks)
        assert not np.allclose(embeddings[0], embeddings[1])

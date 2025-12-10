"""
Local Embeddings
================
Wrapper for local embedding model (sentence-transformers).
"""

from typing import List, Optional
import math

# Lazy load to avoid import time cost
_model = None


def _get_model():
    """Lazy load the embedding model."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer('all-MiniLM-L6-v2')
            print("[INFO] Loaded embedding model: all-MiniLM-L6-v2")
        except ImportError:
            print("[WARN] sentence-transformers not installed. Using fallback.")
            _model = "fallback"
    return _model


def embed(text: str) -> List[float]:
    """Generate embedding for text."""
    model = _get_model()
    
    if model == "fallback":
        # Simple hash-based fallback (not semantic, but works)
        return _fallback_embed(text)
    
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def embed_batch(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for multiple texts efficiently."""
    model = _get_model()
    
    if model == "fallback":
        return [_fallback_embed(t) for t in texts]
    
    embeddings = model.encode(texts, convert_to_numpy=True)
    return [e.tolist() for e in embeddings]


def similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two embeddings."""
    if len(a) != len(b):
        return 0.0
    
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return dot_product / (norm_a * norm_b)


def _fallback_embed(text: str, dim: int = 384) -> List[float]:
    """Simple fallback when sentence-transformers not available."""
    import hashlib
    
    # Create deterministic pseudo-embedding from text hash
    hash_bytes = hashlib.sha384(text.lower().encode()).digest()
    embedding = [b / 255.0 - 0.5 for b in hash_bytes]
    
    # Normalize
    norm = math.sqrt(sum(x * x for x in embedding))
    if norm > 0:
        embedding = [x / norm for x in embedding]
    
    return embedding

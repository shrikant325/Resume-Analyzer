"""
Core AIML similarity component.

  * tfidf_similarity     -> TF-IDF vectors + cosine similarity (always available,
                             scikit-learn only).
  * semantic_similarity  -> optionally uses a pretrained Sentence-Transformer
                             model for embedding-based semantic similarity, as
                             suggested in the project spec. This is opt-in via
                             USE_SENTENCE_TRANSFORMERS=true (and requires
                             `pip install sentence-transformers`) so the app
                             never tries to download a model unexpectedly.
                             When disabled or unavailable, it transparently
                             falls back to the TF-IDF score.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.nlp.preprocess import clean_text_for_vectorizer

_semantic_model = None
_semantic_load_attempted = False


def tfidf_similarity(resume_text, jd_text):
    a = clean_text_for_vectorizer(resume_text)
    b = clean_text_for_vectorizer(jd_text)
    if not a.strip() or not b.strip():
        return 0.0
    vectorizer = TfidfVectorizer()
    try:
        matrix = vectorizer.fit_transform([a, b])
    except ValueError:
        return 0.0
    score = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
    return round(float(score) * 100, 2)


def _load_semantic_model():
    global _semantic_model, _semantic_load_attempted
    if _semantic_load_attempted:
        return _semantic_model
    _semantic_load_attempted = True
    try:
        from sentence_transformers import SentenceTransformer
        _semantic_model = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        _semantic_model = None
    return _semantic_model


def semantic_similarity(resume_text, jd_text, use_transformer=False):
    """Returns (score_0_to_100, method_used)."""
    if use_transformer:
        model = _load_semantic_model()
        if model is not None:
            try:
                embeddings = model.encode([resume_text, jd_text])
                score = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
                return round(float(score) * 100, 2), "sentence-transformers"
            except Exception:
                pass
    return tfidf_similarity(resume_text, jd_text), "tfidf-fallback"

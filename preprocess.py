"""
Text preprocessing pipeline: tokenize -> remove stop-words -> lemmatize.

Design note: this module tries to use NLTK (real tokenizer, real stop-word
corpus, WordNet lemmatizer) *only if its data files are already present*.
It never attempts to download anything at import time or at request time -
that would risk a slow/blocked network call in restricted environments. If
NLTK or its data isn't available, it falls back to a small built-in
regex tokenizer, a bundled stop-word list, and a light suffix-stripping
stemmer, so the app's NLP pipeline always works out of the box.

To enable the full NLTK pipeline: `pip install nltk` then run once (needs
internet):
    python -m nltk.downloader punkt punkt_tab stopwords wordnet omw-1.4
"""

import re

# ---------------------------------------------------------------------------
# Built-in fallback stop-word list (used whenever NLTK's corpus isn't ready)
# ---------------------------------------------------------------------------
_FALLBACK_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any",
    "are", "aren't", "as", "at", "be", "because", "been", "before", "being", "below",
    "between", "both", "but", "by", "can", "could", "did", "do", "does", "doing", "down",
    "during", "each", "few", "for", "from", "further", "had", "has", "have", "having",
    "he", "her", "here", "hers", "herself", "him", "himself", "his", "how", "i", "if",
    "in", "into", "is", "it", "its", "itself", "just", "me", "more", "most", "my",
    "myself", "no", "nor", "not", "now", "of", "off", "on", "once", "only", "or", "other",
    "our", "ours", "ourselves", "out", "over", "own", "s", "same", "she", "should", "so",
    "some", "such", "t", "than", "that", "the", "their", "theirs", "them", "themselves",
    "then", "there", "these", "they", "this", "those", "through", "to", "too", "under",
    "until", "up", "very", "was", "we", "were", "what", "when", "where", "which", "while",
    "who", "whom", "why", "will", "with", "would", "you", "your", "yours", "yourself",
    "yourselves", "also", "etc", "using", "used", "use", "including", "include", "via",
    "per", "within", "across",
}

_nltk_ready = False
_lemmatizer = None
STOP_WORDS = _FALLBACK_STOPWORDS

try:
    import nltk  # noqa: F401
    from nltk.corpus import stopwords as _nltk_stopwords
    from nltk.stem import WordNetLemmatizer as _WordNetLemmatizer
    from nltk.tokenize import word_tokenize as _word_tokenize

    try:
        STOP_WORDS = set(_nltk_stopwords.words("english"))
        _has_stopwords = True
    except LookupError:
        _has_stopwords = False

    try:
        _word_tokenize("Quick availability check.")
        _has_punkt = True
    except LookupError:
        _has_punkt = False

    try:
        _lemmatizer_candidate = _WordNetLemmatizer()
        _lemmatizer_candidate.lemmatize("testing")
        _lemmatizer = _lemmatizer_candidate
        _has_wordnet = True
    except LookupError:
        _has_wordnet = False

    _nltk_ready = _has_punkt
    if not _has_stopwords:
        STOP_WORDS = _FALLBACK_STOPWORDS
except Exception:
    _nltk_ready = False
    _lemmatizer = None
    STOP_WORDS = _FALLBACK_STOPWORDS


_WORD_RE = re.compile(r"[A-Za-z][A-Za-z\-\+\#\.]*")


def tokenize(text):
    text = text or ""
    if _nltk_ready:
        try:
            from nltk.tokenize import word_tokenize
            return [t for t in word_tokenize(text) if any(c.isalpha() for c in t)]
        except Exception:
            pass
    return _WORD_RE.findall(text)


def remove_stopwords(tokens):
    return [t for t in tokens if t.lower() not in STOP_WORDS and len(t) > 1]


def _simple_stem(word):
    for suffix in ("edly", "ing", "ies", "ied", "es", "ed", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def lemmatize(tokens):
    if _lemmatizer is not None:
        try:
            return [_lemmatizer.lemmatize(t.lower()) for t in tokens]
        except Exception:
            pass
    return [_simple_stem(t.lower()) for t in tokens]


def preprocess(text):
    """Full pipeline: tokenize -> remove stop-words -> lemmatize."""
    tokens = tokenize(text)
    tokens = remove_stopwords(tokens)
    tokens = lemmatize(tokens)
    return tokens


def clean_text_for_vectorizer(text):
    """Preprocessed text as a single space-joined string, ready for TF-IDF."""
    return " ".join(preprocess(text))

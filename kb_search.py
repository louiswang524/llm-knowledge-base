#!/usr/bin/env python3
"""
KB Search — personal knowledge base search CLI.

Usage:
  python3 kb_search.py --rebuild               # build/update search index
  python3 kb_search.py "query" [--top N]       # search the wiki
"""

import argparse
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config() -> Path:
    kb_path = Path.cwd()
    while kb_path != kb_path.parent:
        if (kb_path / "kb-manifest.json").exists():
            return kb_path.resolve()
        kb_path = kb_path.parent
    print(json.dumps({"error": "Not inside a knowledge base (kb-manifest.json not found)."}))
    sys.exit(1)


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter block."""
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            return text[end + 3:].strip()
    return text


def extract_title(text: str) -> str:
    """Extract first # heading or return empty string."""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens, strip punctuation."""
    return re.findall(r"[a-z0-9]+", text.lower())


def extract_snippet(body: str, query_terms: list[str], max_len: int = 160) -> str:
    """Find the sentence with the most query term hits."""
    sentences = re.split(r"(?<=[.!?])\s+", body)
    best_sentence = ""
    best_score = -1
    for sentence in sentences:
        tokens = set(tokenize(sentence))
        score = sum(1 for t in query_terms if t in tokens)
        if score > best_score:
            best_score = score
            best_sentence = sentence.strip()
    snippet = best_sentence[:max_len]
    if len(best_sentence) > max_len:
        snippet += "..."
    return snippet


# ---------------------------------------------------------------------------
# TF-IDF keyword scoring
# ---------------------------------------------------------------------------

def compute_tfidf(entries: list[dict]) -> list[dict]:
    """
    Compute TF-IDF term weights for each entry.
    Stores a dict of {term: weight} per entry.
    Title terms get 3x weight boost.
    """
    # Build document frequency counts
    df: dict[str, int] = {}
    N = len(entries)
    tokenized = []
    for entry in entries:
        title_tokens = tokenize(entry["title"]) * 3  # title boost
        body_tokens = tokenize(entry["body"])
        all_tokens = title_tokens + body_tokens
        tokenized.append(all_tokens)
        for term in set(all_tokens):
            df[term] = df.get(term, 0) + 1

    for i, entry in enumerate(entries):
        tokens = tokenized[i]
        tf: dict[str, float] = {}
        for term in tokens:
            tf[term] = tf.get(term, 0) + 1
        total = len(tokens) or 1
        tfidf: dict[str, float] = {}
        for term, count in tf.items():
            idf = math.log((N + 1) / (df.get(term, 0) + 1)) + 1
            tfidf[term] = (count / total) * idf
        entry["tfidf"] = tfidf

    return entries


def keyword_score(query: str, entry: dict) -> float:
    """Score an entry against a query using TF-IDF term overlap."""
    query_terms = tokenize(query)
    tfidf = entry.get("tfidf", {})
    if not query_terms or not tfidf:
        return 0.0
    score = sum(tfidf.get(term, 0.0) for term in query_terms)
    # Normalize by query length
    return score / len(query_terms)


# ---------------------------------------------------------------------------
# Semantic search (sentence-transformers)
# ---------------------------------------------------------------------------

def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def load_embedder():
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer("all-MiniLM-L6-v2")
    except ImportError:
        return None


def embed_text(model, text: str) -> list[float]:
    return model.encode(text, convert_to_numpy=True).tolist()


# ---------------------------------------------------------------------------
# Index build
# ---------------------------------------------------------------------------

WIKI_DIRS = ["wiki/concepts", "wiki/sources"]
INDEX_PATH_REL = ".kb/search_index.json"


def scan_wiki_files(kb_path: Path) -> list[Path]:
    files = []
    for d in WIKI_DIRS:
        dirpath = kb_path / d
        if dirpath.exists():
            files.extend(sorted(dirpath.glob("*.md")))
    return files


def build_index(kb_path: Path) -> dict:
    print("Scanning wiki files...", file=sys.stderr)
    files = scan_wiki_files(kb_path)

    if not files:
        print("No wiki files found. Run /kb-compile first.", file=sys.stderr)
        return {"built_at": datetime.now(timezone.utc).isoformat(), "entries": []}

    # Load embedder (optional)
    embedder = load_embedder()
    if embedder:
        print(f"Loaded sentence-transformers (all-MiniLM-L6-v2)", file=sys.stderr)
    else:
        print("sentence-transformers not installed — semantic search disabled.", file=sys.stderr)
        print("Install with: pip install sentence-transformers", file=sys.stderr)

    entries = []
    for fpath in files:
        rel = str(fpath.relative_to(kb_path))
        raw = fpath.read_text(encoding="utf-8")
        body = strip_frontmatter(raw)
        title = extract_title(body) or fpath.stem.replace("-", " ").title()

        entry = {
            "file": rel,
            "title": title,
            "body": body,
            "embedding": embed_text(embedder, title + " " + body[:512]) if embedder else None,
        }
        entries.append(entry)
        print(f"  Indexed: {rel}", file=sys.stderr)

    # Compute TF-IDF weights
    entries = compute_tfidf(entries)

    # Strip body from stored index to keep file size down — keep only snippet source
    index = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "has_embeddings": embedder is not None,
        "entries": [
            {
                "file": e["file"],
                "title": e["title"],
                "body": e["body"],       # kept for snippet extraction
                "tfidf": e["tfidf"],
                "embedding": e["embedding"],
            }
            for e in entries
        ],
    }

    index_path = kb_path / INDEX_PATH_REL
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

    print(f"\nIndex built: {len(entries)} entries → {index_path}", file=sys.stderr)
    return index


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

KEYWORD_THRESHOLD = 0.05   # below this, fall back to semantic
TOP_DEFAULT = 5


def search(kb_path: Path, query: str, top_n: int = TOP_DEFAULT) -> dict:
    index_path = kb_path / INDEX_PATH_REL
    if not index_path.exists():
        return {
            "error": "Search index not found. Run: python3 kb_search.py --rebuild",
            "query": query,
        }

    with open(index_path, encoding="utf-8") as f:
        index = json.load(f)

    entries = index["entries"]
    query_terms = tokenize(query)

    # --- Keyword scoring ---
    scored = [(keyword_score(query, e), e) for e in entries]
    scored.sort(key=lambda x: x[0], reverse=True)
    best_keyword_score = scored[0][0] if scored else 0.0

    if best_keyword_score >= KEYWORD_THRESHOLD:
        mode = "keyword"
        results = scored[:top_n]
    elif index.get("has_embeddings"):
        # --- Semantic fallback ---
        mode = "semantic"
        embedder = load_embedder()
        if embedder is None:
            # Embedder was available at index build but not now — fall back to keyword
            mode = "keyword"
            results = scored[:top_n]
        else:
            query_vec = embed_text(embedder, query)
            sem_scored = [
                (cosine_similarity(query_vec, e["embedding"]) if e.get("embedding") else 0.0, e)
                for e in entries
            ]
            sem_scored.sort(key=lambda x: x[0], reverse=True)
            results = sem_scored[:top_n]
    else:
        mode = "keyword"
        results = scored[:top_n]

    output_results = []
    for score, entry in results:
        if score <= 0:
            continue
        snippet = extract_snippet(entry["body"], query_terms)
        output_results.append({
            "file": entry["file"],
            "title": entry["title"],
            "score": round(float(score), 4),
            "snippet": snippet,
        })

    return {
        "query": query,
        "mode": mode,
        "results": output_results,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="KB Search CLI")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild the search index")
    parser.add_argument("--top", type=int, default=TOP_DEFAULT, help="Number of results (default 5)")
    args = parser.parse_args()

    kb_path = load_config()

    if args.rebuild:
        build_index(kb_path)
        return

    if not args.query:
        parser.print_help()
        sys.exit(1)

    result = search(kb_path, args.query, top_n=args.top)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

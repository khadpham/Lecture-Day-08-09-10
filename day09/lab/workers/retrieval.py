"""
workers/retrieval.py — Retrieval Worker
Sprint 2: Implement retrieval từ ChromaDB, trả về chunks + sources.

Input (từ AgentState):
    - task: câu hỏi cần retrieve
    - (optional) retrieved_chunks nếu đã có từ trước

Output (vào AgentState):
    - retrieved_chunks: list of {"text", "source", "score", "metadata"}
    - retrieved_sources: list of source filenames
    - worker_io_log: log input/output của worker này

Gọi độc lập để test:
    python workers/retrieval.py
"""

import os
import sys
import re
import contextlib
import io
import warnings
from functools import lru_cache

# ─────────────────────────────────────────────
# Worker Contract (xem contracts/worker_contracts.yaml)
# Input:  {"task": str, "top_k": int = 3}
# Output: {"retrieved_chunks": list, "retrieved_sources": list, "error": dict | None}
# ─────────────────────────────────────────────

WORKER_NAME = "retrieval_worker"
DEFAULT_TOP_K = 3
DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "docs")

STOPWORDS = {
    "là", "và", "hay", "hoặc", "của", "cho", "với", "trong", "theo", "khi",
    "bao", "nhiêu", "như", "thế", "nào", "ai", "gì", "ở", "được", "có", "không",
    "if", "the", "a", "an", "to", "for", "of", "in", "on", "is", "are", "be",
}

NUMERIC_QUESTION_MARKERS = (
    "bao nhiêu",
    "bao lâu",
    "mấy",
    "khi nào",
    "lúc mấy",
    "thời gian",
    "trong vòng",
    "sau bao",
)

ERROR_QUERY_PATTERN = re.compile(r"\b(?:err[-_ ]?[a-z0-9]+)\b", re.IGNORECASE)

DOC_HINTS = {
    "policy_refund_v4.txt": ["hoàn", "refund", "flash", "sale", "license", "subscription", "digital"],
    "sla_p1_2026.txt": ["sla", "p1", "escalation", "incident", "ticket"],
    "access_control_sop.txt": ["quyền", "access", "level", "admin", "phê", "duyệt"],
    "hr_leave_policy.txt": ["remote", "nghỉ", "phép", "leave", "team", "lead"],
    "it_helpdesk_faq.txt": ["helpdesk", "jira", "laptop", "mật", "khẩu", "đăng", "nhập"],
}


@lru_cache(maxsize=1)
def _load_sentence_transformer_model():
    """Load the embedding model once and keep Hugging Face quiet."""
    from transformers.utils import logging as hf_logging
    from huggingface_hub import logging as hf_hub_logging

    hf_logging.set_verbosity_error()
    hf_hub_logging.set_verbosity_error()
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    warnings.filterwarnings("ignore", message=".*UNEXPECTED.*")
    warnings.filterwarnings("ignore", message=".*LOAD REPORT.*")

    from sentence_transformers import SentenceTransformer

    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return SentenceTransformer("all-MiniLM-L6-v2")


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 4)


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"\b\w+\b", text.lower(), flags=re.UNICODE)
    return {tok for tok in tokens if tok and tok not in STOPWORDS}


def _lexical_score(query_tokens: set[str], text: str) -> float:
    if not query_tokens:
        return 0.0

    text_tokens = _tokenize(text)
    if not text_tokens:
        return 0.0

    overlap = len(query_tokens & text_tokens)
    if overlap <= 0:
        return 0.0

    denom = max(1, min(len(query_tokens), 6))
    return _clamp_score(overlap / denom)


def _is_numeric_query(query: str) -> bool:
    lower = (query or "").lower()
    return any(marker in lower for marker in NUMERIC_QUESTION_MARKERS)


def _contains_number(text: str) -> bool:
    return bool(re.search(r"\d", text or ""))


def _is_error_lookup_query(query: str) -> bool:
    return bool(ERROR_QUERY_PATTERN.search(query or ""))


def _normalize_alnum(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def _line_score(query_tokens: set[str], line: str, numeric_query: bool) -> float:
    line_tokens = _tokenize(line)
    if not query_tokens or not line_tokens:
        return 0.0

    overlap = len(query_tokens & line_tokens)
    if overlap <= 0:
        return 0.0

    score = overlap / max(1, min(len(query_tokens), 6))

    # Numeric questions should prefer lines containing concrete numbers.
    if numeric_query and _contains_number(line):
        score += 0.25

    # Penalize section headings (often broad, less factual).
    compact = line.strip()
    if compact.startswith("===") or (compact.isupper() and len(compact.split()) <= 12):
        score -= 0.1

    return _clamp_score(score)


def _best_line_for_doc(lines: list[str], query_tokens: set[str], numeric_query: bool) -> tuple[str, float]:
    best_line = lines[0]
    best_score = 0.0

    for line in lines:
        line_score = _line_score(query_tokens, line, numeric_query)
        if line_score > best_score:
            best_score = line_score
            best_line = line

    return best_line, best_score


def _pick_hint_doc(query: str) -> str | None:
    q = query.lower()
    best_doc = None
    best_score = 0

    for doc_name, hints in DOC_HINTS.items():
        score = sum(1 for hint in hints if hint in q)
        if score > best_score:
            best_score = score
            best_doc = doc_name

    return best_doc if best_score > 0 else None


@lru_cache(maxsize=1)
def _load_local_docs() -> list[tuple[str, str]]:
    docs: list[tuple[str, str]] = []
    if not os.path.isdir(DOCS_DIR):
        return docs

    for fname in sorted(os.listdir(DOCS_DIR)):
        if not fname.endswith(".txt"):
            continue
        fpath = os.path.join(DOCS_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                docs.append((fname, f.read()))
        except OSError:
            continue
    return docs


def _local_retrieve(query: str, top_k: int = DEFAULT_TOP_K) -> list:
    """Fallback retrieval from local docs when Chroma is unavailable/empty."""
    q_tokens = _tokenize(query)
    numeric_query = _is_numeric_query(query)
    error_lookup_query = _is_error_lookup_query(query)
    scored: list[tuple[float, str, str]] = []

    for source, text in _load_local_docs():
        lines = [ln.strip(" -*\t") for ln in text.splitlines() if ln.strip()]
        if not lines:
            continue

        best_line, best_score = _best_line_for_doc(lines, q_tokens, numeric_query)
        if q_tokens and best_score > 0:
            score = best_score
            scored.append((_clamp_score(score), source, best_line))

    scored.sort(key=lambda x: x[0], reverse=True)

    if error_lookup_query:
        error_codes = [_normalize_alnum(code) for code in ERROR_QUERY_PATTERN.findall(query) if code]
        has_direct_error_match = False
        for _, _, line in scored:
            normalized_line = _normalize_alnum(line)
            if any(code and code in normalized_line for code in error_codes):
                has_direct_error_match = True
                break
        if not has_direct_error_match:
            return []

    quality_floor = 0.3 if numeric_query else 0.22
    selected = [item for item in scored if item[0] >= quality_floor][:top_k]

    # For unknown error-code lookups, abstain instead of forcing unrelated evidence.
    if error_lookup_query and not selected:
        return []

    if not selected and _load_local_docs():
        hinted_doc = _pick_hint_doc(query)
        docs_map = {name: content for name, content in _load_local_docs()}
        if hinted_doc and hinted_doc in docs_map:
            text = docs_map[hinted_doc]
            hint_lines = [ln.strip(" -*\t") for ln in text.splitlines() if ln.strip()]
            if hint_lines:
                hint_line, hint_score = _best_line_for_doc(hint_lines, q_tokens, numeric_query)
                selected = [(max(0.32, hint_score), hinted_doc, hint_line)]
            else:
                selected = [(0.32, hinted_doc, text[:180])]

    if not selected and _load_local_docs() and not error_lookup_query:
        source, text = _load_local_docs()[0]
        first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), text[:180])
        selected = [(0.2, source, first_line)]

    chunks = []
    for idx, (score, source, snippet) in enumerate(selected, start=1):
        chunks.append(
            {
                "text": snippet,
                "source": source,
                "score": _clamp_score(score),
                "metadata": {
                    "retrieval_mode": "local_fallback",
                    "rank": idx,
                },
            }
        )
    return chunks


def _get_embedding_fn():
    """
    Trả về embedding function.
    TODO Sprint 1: Implement dùng OpenAI hoặc Sentence Transformers.
    """
    # Option A: Sentence Transformers (offline, không cần API key)
    try:
        model = _load_sentence_transformer_model()
        def embed(text: str) -> list:
            return model.encode([text])[0].tolist()
        return embed
    except ImportError:
        pass

    # Option B: OpenAI (cần API key)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        def embed(text: str) -> list:
            resp = client.embeddings.create(input=text, model="text-embedding-3-small")
            return resp.data[0].embedding
        return embed
    except ImportError:
        pass

    # Fallback: random embeddings cho test (KHÔNG dùng production)
    import random
    def embed(text: str) -> list:
        return [random.random() for _ in range(384)]
    print("⚠️  WARNING: Using random embeddings (test only). Install sentence-transformers.")
    return embed


def _get_collection():
    """
    Kết nối ChromaDB collection.
    TODO Sprint 2: Đảm bảo collection đã được build từ Step 3 trong README.
    """
    import chromadb
    client = chromadb.PersistentClient(path="./chroma_db")
    try:
        collection = client.get_collection("day09_docs")
    except Exception:
        # Auto-create nếu chưa có
        collection = client.get_or_create_collection(
            "day09_docs",
            metadata={"hnsw:space": "cosine"}
        )
        print(f"⚠️  Collection 'day09_docs' chưa có data. Chạy index script trong README trước.")
    return collection


def retrieve_dense(query: str, top_k: int = DEFAULT_TOP_K) -> list:
    """
    Dense retrieval: embed query → query ChromaDB → trả về top_k chunks.

    TODO Sprint 2: Implement phần này.
    - Dùng _get_embedding_fn() để embed query
    - Query collection với n_results=top_k
    - Format result thành list of dict

    Returns:
        list of {"text": str, "source": str, "score": float, "metadata": dict}
    """
    # TODO: Implement dense retrieval
    embed = _get_embedding_fn()
    query_embedding = embed(query)
    query_tokens = _tokenize(query)

    try:
        collection = _get_collection()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "distances", "metadatas"]
        )

        chunks = []
        for doc, dist, meta in zip(
            results["documents"][0],
            results["distances"][0],
            results["metadatas"][0]
        ):
            similarity = _clamp_score(1 - float(dist))
            lexical = _lexical_score(query_tokens, doc)
            blended = _clamp_score((0.7 * similarity) + (0.3 * lexical))
            chunks.append({
                "text": doc,
                "source": (meta or {}).get("source", "unknown"),
                "score": blended,
                "metadata": meta or {},
            })

        strong_chunks = [c for c in chunks if c.get("score", 0.0) >= 0.22]
        if strong_chunks:
            chunks = strong_chunks[:top_k]
        elif chunks:
            chunks = sorted(chunks, key=lambda c: c.get("score", 0.0), reverse=True)[:1]

        if not chunks:
            return _local_retrieve(query, top_k=top_k)
        return chunks

    except Exception as e:
        print(f"⚠️  ChromaDB query failed: {e}")
        # Fallback: local docs retrieval
        return _local_retrieve(query, top_k=top_k)


def run(state: dict) -> dict:
    """
    Worker entry point — gọi từ graph.py.

    Args:
        state: AgentState dict

    Returns:
        Updated AgentState với retrieved_chunks và retrieved_sources
    """
    task = state.get("task", "")
    top_k = state.get("top_k", state.get("retrieval_top_k", DEFAULT_TOP_K))

    state.setdefault("workers_called", [])
    state.setdefault("history", [])

    state["workers_called"].append(WORKER_NAME)

    # Log worker IO (theo contract)
    worker_io = {
        "worker": WORKER_NAME,
        "input": {"task": task, "top_k": top_k},
        "output": None,
        "error": None,
    }

    try:
        chunks = retrieve_dense(task, top_k=int(top_k))

        sources = list({c["source"] for c in chunks})

        state["retrieved_chunks"] = chunks
        state["retrieved_sources"] = sources

        worker_io["output"] = {
            "chunks_count": len(chunks),
            "sources": sources,
        }
        state["history"].append(
            f"[{WORKER_NAME}] retrieved {len(chunks)} chunks from {sources}"
        )

    except Exception as e:
        worker_io["error"] = {"code": "RETRIEVAL_FAILED", "reason": str(e)}
        state["retrieved_chunks"] = []
        state["retrieved_sources"] = []
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    # Ghi worker IO vào state để trace
    state.setdefault("worker_io_logs", []).append(worker_io)

    return state


# ─────────────────────────────────────────────
# Test độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Retrieval Worker — Standalone Test")
    print("=" * 50)

    test_queries = [
        "SLA ticket P1 là bao lâu?",
        "Điều kiện được hoàn tiền là gì?",
        "Ai phê duyệt cấp quyền Level 3?",
    ]

    for query in test_queries:
        print(f"\n▶ Query: {query}")
        result = run({"task": query})
        chunks = result.get("retrieved_chunks", [])
        print(f"  Retrieved: {len(chunks)} chunks")
        for c in chunks[:2]:
            print(f"    [{c['score']:.3f}] {c['source']}: {c['text'][:80]}...")
        print(f"  Sources: {result.get('retrieved_sources', [])}")

    print("\n✅ retrieval_worker test done.")

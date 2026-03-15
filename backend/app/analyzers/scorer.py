"""Developer relevance scoring heuristics."""
from __future__ import annotations

import re

# High-signal keywords → importance boost
HIGH_IMPORTANCE_KEYWORDS = [
    "api", "sdk", "launch", "release", "gpt", "claude", "gemini", "llama",
    "agent", "autonomous", "rag", "retrieval", "vector", "embedding",
    "inference", "fine-tuning", "finetune", "lora", "quantization",
    "cuda", "gpu", "benchmark", "context window", "multimodal",
    "open source", "open-source", "hugging face", "pytorch", "transformer",
    "langchain", "llamaindex", "openai", "anthropic", "google deepmind",
]

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "model_llm": ["gpt", "claude", "gemini", "llama", "mixtral", "mistral", "model", "llm", "language model"],
    "ai_agent": ["agent", "autonomous", "tool use", "function call", "workflow", "orchestration"],
    "infra_serving": ["inference", "serving", "deployment", "cuda", "gpu", "triton", "vllm", "kubernetes", "k8s"],
    "opensource_framework": ["open source", "open-source", "github", "hugging face", "pytorch", "tensorflow", "jax"],
    "product_launch": ["launch", "release", "announce", "available", "preview", "beta", "ga"],
    "research_paper": ["arxiv", "paper", "benchmark", "study", "dataset", "evaluation", "survey"],
    "security_policy": ["safety", "alignment", "bias", "regulation", "policy", "privacy", "attack", "jailbreak"],
    "dev_tools": ["ide", "plugin", "extension", "copilot", "code", "cursor", "devtool"],
}


def score_article(title: str, text: str | None) -> dict:
    """Return scoring dict with individual scores and category guess."""
    combined = (title + " " + (text or "")).lower()

    importance = _keyword_score(combined, HIGH_IMPORTANCE_KEYWORDS, max_score=1.0)
    novelty = _novelty_indicators(combined)
    dev_relevance = _dev_relevance(combined)

    composite = round((importance * 0.4 + novelty * 0.2 + dev_relevance * 0.4), 3)
    category = _guess_category(combined)

    return {
        "importance_score": round(importance, 3),
        "novelty_score": round(novelty, 3),
        "developer_relevance_score": round(dev_relevance, 3),
        "composite_score": composite,
        "category": category,
        "details": {
            "matched_importance_keywords": _matched_keywords(combined, HIGH_IMPORTANCE_KEYWORDS),
        },
    }


def _keyword_score(text: str, keywords: list[str], max_score: float = 1.0) -> float:
    matched = sum(1 for kw in keywords if kw in text)
    return min(matched / max(len(keywords) * 0.15, 1), max_score)


def _novelty_indicators(text: str) -> float:
    signals = [
        "first", "new", "announce", "introduce", "launch", "release",
        "break", "record", "state-of-the-art", "sota", "novel", "breakthrough",
    ]
    return _keyword_score(text, signals, max_score=1.0)


def _dev_relevance(text: str) -> float:
    dev_signals = [
        "api", "sdk", "github", "pip install", "docker", "kubernetes",
        "open source", "python", "javascript", "typescript", "rust",
        "vector db", "embedding", "rag", "fine-tun", "quantiz",
        "inference", "serving", "latency", "throughput", "token",
    ]
    return _keyword_score(text, dev_signals, max_score=1.0)


def _guess_category(text: str) -> str:
    scores: dict[str, int] = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        scores[cat] = sum(1 for kw in keywords if kw in text)
    if not any(scores.values()):
        return "other"
    return max(scores, key=lambda k: scores[k])


def _matched_keywords(text: str, keywords: list[str]) -> list[str]:
    return [kw for kw in keywords if kw in text][:10]

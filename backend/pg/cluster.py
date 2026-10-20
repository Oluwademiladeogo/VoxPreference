"""Two-level clustering of tokens of the unit under study, and the contrastiveness matrix.

Primary clusters are phonological categories (the variant each token was judged to realise).
Secondary clusters split each category by acoustic similarity (cosine distance between
self-supervised speech features of the segment), exposing sub-variants and outliers.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _unit(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x, axis=1, keepdims=True)
    return x / np.where(n == 0, 1, n)


@dataclass
class Clustering:
    primary: list[str]  # per token
    secondary: list[str]  # per token, e.g. "t.1"
    categories: list[str]  # primary cluster names, most frequent first
    contrast: np.ndarray  # cosine similarity between category centroids (categories x categories)
    separation: dict[str, float]  # mean silhouette of each category (higher = more distinct)


def kmeans_cosine(x: np.ndarray, k: int, seed: int = 0) -> np.ndarray:
    from sklearn.cluster import KMeans

    return KMeans(n_clusters=k, n_init=10, random_state=seed).fit_predict(_unit(x))


def _best_split(x: np.ndarray, k_max: int, min_size: int, seed: int):
    from sklearn.metrics import silhouette_score

    best_labels, best_score = None, -1.0
    for k in range(2, min(k_max, len(x) // min_size) + 1):
        labels = kmeans_cosine(x, k, seed)
        if np.bincount(labels).min() < min_size:
            continue
        score = silhouette_score(_unit(x), labels, metric="cosine")
        if score > best_score:
            best_labels, best_score = labels, score
    return best_labels, best_score


def _reference(x: np.ndarray, rng) -> np.ndarray:
    """A structureless sample with the same spread: one Gaussian aligned with x's principal axes."""
    mean = x.mean(0)
    _, s, vt = np.linalg.svd(x - mean, full_matrices=False)
    sd = s / np.sqrt(max(len(x) - 1, 1))
    return mean + (rng.standard_normal((len(x), len(sd))) * sd) @ vt


def choose_k(x: np.ndarray, k_max: int, min_size: int = 3, seed: int = 0, margin: float = 0.1) -> np.ndarray:
    """Split into k (2..k_max) clusters only if the best split's cosine silhouette clearly beats that of
    structureless reference data with the same principal-axis spread (gap-statistic style); else one cluster."""
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    labels, score = _best_split(x, k_max, min_size, seed)
    if labels is None:
        return np.zeros(n, dtype=int)
    rng = np.random.default_rng(seed)
    null = max(_best_split(_reference(x, rng), k_max, min_size, seed)[1] for _ in range(3))
    if score < null + margin:
        return np.zeros(n, dtype=int)
    return labels


def two_level(labels: list[str], embeddings: np.ndarray | None, max_sub: int = 3) -> Clustering:
    counts = {c: labels.count(c) for c in dict.fromkeys(labels)}
    categories = sorted(counts, key=lambda c: -counts[c])
    secondary = list(labels)
    contrast = np.eye(len(categories))
    separation = {c: float("nan") for c in categories}
    if embeddings is not None and len(embeddings) == len(labels):
        x = np.asarray(embeddings, dtype=np.float64)
        # centre first: raw self-supervised features share a large common direction, so uncentred
        # cosine similarities are all high (0.7-0.95) whatever the sounds
        x = _unit(x - x.mean(0))
        lab = np.array(labels)
        for c in categories:
            idx = np.where(lab == c)[0]
            sub = choose_k(x[idx], max_sub) if len(idx) >= 6 else np.zeros(len(idx), dtype=int)
            # number sub-clusters by size so ".1" is always the core of the category
            order = {s: r + 1 for r, s in enumerate(sorted(set(sub), key=lambda s: -(sub == s).sum()))}
            for i, s in zip(idx, sub):
                secondary[i] = f"{c}.{order[s]}"
        centroids = np.stack([x[lab == c].mean(0) for c in categories])
        contrast = _unit(centroids) @ _unit(centroids).T
        # silhouettes need at least one category with two tokens (2 <= categories <= tokens - 1)
        if 1 < len(categories) < len(labels):
            from sklearn.metrics import silhouette_samples

            sil = silhouette_samples(x, lab, metric="cosine")
            separation = {c: float(sil[lab == c].mean()) for c in categories}
    return Clustering(labels, secondary, categories, contrast, separation)


def purity(pred: list, truth: list) -> float:
    """Share of tokens whose cluster's majority truth label matches their own (1.0 = clusters are pure)."""
    total = 0
    for c in set(pred):
        members = [t for p, t in zip(pred, truth) if p == c]
        total += max(members.count(t) for t in set(members))
    return total / len(pred)

import numpy as np

from pg.cluster import choose_k, purity, two_level


def blobs(centres, n, noise=0.05, seed=0):
    rng = np.random.default_rng(seed)
    return np.concatenate([c + noise * rng.standard_normal((n, len(c))) for c in centres])


def test_two_level_finds_sub_variants_and_contrast():
    d = 16
    e = np.eye(d)
    # category "t" has two acoustic sub-variants (think alveolar vs dental), "θ" is one tight group
    t_emb = blobs([e[0] + e[1], e[0] - e[1]], 10)
    th_emb = blobs([e[5]], 12)
    labels = ["t"] * 20 + ["θ"] * 12
    res = two_level(labels, np.concatenate([t_emb, th_emb]))
    assert res.categories == ["t", "θ"]
    assert sorted(set(res.secondary[:20])) == ["t.1", "t.2"]
    assert set(res.secondary[20:]) == {"θ.1"}
    assert res.contrast.shape == (2, 2) and res.contrast[0, 1] < 0.5
    assert res.separation["θ"] > 0.5


def test_no_split_without_structure():
    x = np.random.default_rng(1).standard_normal((30, 8))
    assert len(set(choose_k(x, 3))) == 1


def test_two_level_without_embeddings_keeps_categories():
    res = two_level(["a", "b", "a"], None)
    assert res.categories == ["a", "b"] and res.secondary == ["a", "b", "a"]


def test_purity():
    assert purity([0, 0, 1, 1], ["x", "x", "y", "y"]) == 1.0
    assert purity([0, 0, 0, 0], ["x", "x", "y", "y"]) == 0.5

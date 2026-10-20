from pathlib import Path

from fastapi.testclient import TestClient

import app

client = TestClient(app.app)
TEMPLATE = Path(__file__).resolve().parents[2] / "templates" / "expert_variant_annotations.csv"
THINK = {
    "target_word": "think",
    "reference_ipa": "θɪŋk",
    "variants": [
        {"ipa": "θɪŋk", "count": 4, "label": "international-like"},
        {"ipa": "tɪŋk", "count": 9, "label": "alveolar stop"},
        {"ipa": "sɪŋk", "count": 2, "label": "fricative replacement"},
    ],
    "sliders": {"IA": 6, "CO": 5, "F": 4, "DI": 3, "PS": 2, "PC": 1},
}


def test_preference_analyze_returns_an_operability_table():
    r = client.post("/preference/analyze", json=THINK)
    assert r.status_code == 200, r.text
    body = r.json()
    # Ugorji's think tableau: strict ranking prefers [θɪŋk] although [tɪŋk] is commoner
    assert body["success"] and body["scoring"] == "strict" and body["bestTranscription"] == "θɪŋk"
    assert {row["ipa"]: row["outcome"] for row in body["tableRows"]} == {
        "θɪŋk": "preferred", "tɪŋk": "out at DisaM", "sɪŋk": "out at I-Ac"}


def test_slider_order_sets_the_ranking():
    from pg.pg2_bridge import ranking_from

    assert ranking_from({"sliders": {"IA": 6, "CO": 5, "F": 4, "DI": 3, "PS": 2, "PC": 1}}) == \
        "I-Ac >> ContR >> FreQ >> DisaM >> Pho-S >> Ped-C"
    assert ranking_from({"sliders": {"F": 6, "IA": 3, "CO": 3, "DI": 0, "PS": 1, "PC": 1}}) == \
        "FreQ >> I-Ac, ContR >> Pho-S, Ped-C"


def test_variants_that_do_not_line_up_fall_back_to_the_weighted_method():
    payload = {"target_word": "think", "variants": [{"ipa": "tɪŋk", "count": 9}, {"ipa": "θɪŋkə", "count": 4}]}
    body = client.post("/preference/analyze", json=payload).json()
    assert body["success"] and body["method"] == "pg_core_v1_direct_ipa"
    assert "weighted method" in body["warnings"][-1]


def test_preference_analyze_rejects_bad_json():
    r = client.post("/preference/analyze", content=b"{not json", headers={"content-type": "application/json"})
    assert r.status_code == 400 and not r.json()["success"]


def test_preference_analyze_csv_accepts_the_annotation_template():
    with TEMPLATE.open("rb") as f:
        r = client.post("/preference/analyze-csv", files={"annotationFile": ("a.csv", f, "text/csv")})
    assert r.status_code == 200, r.text
    assert r.json()["success"]


def test_pages_of_the_single_page_app_fall_back_to_index():
    if not app.FRONTEND_DIST.is_dir():
        return
    r = client.get("/criteria")
    assert r.status_code == 200 and "<div id=\"root\">" in r.text

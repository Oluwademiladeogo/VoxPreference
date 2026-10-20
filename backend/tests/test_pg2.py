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
    assert body["success"] and body["bestTranscription"] in {"θɪŋk", "tɪŋk", "sɪŋk"}
    assert len(body["tableRows"]) == 3


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

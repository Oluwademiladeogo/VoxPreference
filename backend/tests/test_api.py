from fastapi.testclient import TestClient

import app


def test_units_endpoint_lists_knowledge_base():
    client = TestClient(app.app)
    r = client.get("/pg/units")
    assert r.status_code == 200
    body = r.json()
    assert "TH-voiceless" in body["units"] and body["units"]["TH-voiceless"]["phoneme"] == "θ"
    assert body["default_ranking"].startswith("I-Ac >>") and len(body["tenets"]) == 6


def test_analyze_rejects_bad_input_without_loading_models(monkeypatch):
    class Boom:
        def analyse(self, *a, **k):
            raise ValueError("give at least one target word")

    monkeypatch.setattr(app, "get_analyzer", lambda: Boom())
    client = TestClient(app.app)
    r = client.post("/pg/analyze", data={"words": " "}, files={"files": ("x.wav", b"RIFF0000WAVE", "audio/wav")})
    assert r.status_code == 400 and r.json()["success"] is False


def test_unknown_setting_is_a_clear_400(monkeypatch):
    monkeypatch.setattr(app, "get_analyzer", lambda: None)
    client = TestClient(app.app)
    r = client.post("/pg/analyze", data={"words": "think", "settings": '{"phos_threshold": 0.2}'},
                    files={"files": ("x.wav", b"RIFF0000WAVE", "audio/wav")})
    assert r.status_code == 400 and "phos_threshold" in r.json()["error"] and "phos_world_threshold" in r.json()["error"]

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_opportunities_summary_has_total():
    res = client.get("/v1/opportunities/summary")
    assert res.status_code == 200
    body = res.json()
    assert "total" in body
    assert body["total"] >= 0
    assert "by_source" in body


def test_opportunities_list_returns_items_shape():
    res = client.get("/v1/opportunities", params={"limit": 5, "offset": 0})
    assert res.status_code == 200
    body = res.json()
    assert "total" in body
    assert "items" in body
    assert isinstance(body["items"], list)
    if body["items"]:
        item = body["items"][0]
        for key in ("title", "source_dataset", "country_norm", "has_contact", "signal_note"):
            assert key in item

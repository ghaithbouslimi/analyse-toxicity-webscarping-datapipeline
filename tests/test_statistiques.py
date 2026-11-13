from datetime import UTC, datetime

from conftest import FauxService

from analyse_toxicite.statistiques import calculer


def test_denominateur_et_relance(depot):
    date = datetime.now(UTC)
    run = {
        "_id": "run",
        "sources": [{"id": "test"}, {"id": "absent"}],
        "start": date,
        "end": date,
        "scoring_hash": "test-config",
    }
    for index, category in enumerate(["non_toxique", "legerement_toxique", "tres_toxique"]):
        article = {
            "canonical_url": f"https://example.com/{index}",
            "article_id": str(index),
            "content_hash": str(index),
            "text": "Texte test",
            "site": "test",
        }
        result = {**FauxService().predire("Texte test"), "category": category}
        key = depot.prediction_batch("run", article, result)
        assert depot.prediction_batch("run", article, result) == key
        depot.observation(
            "run", article["canonical_url"], "test", status="scored", prediction_id=key
        )
    depot.observation("run", "https://example.com/paywall", "test", status="paywall")
    depot.prediction_api("Texte libre", None, FauxService().predire("Texte libre"))
    rows = calculer(depot, run)
    assert rows[0]["scored"] == 3
    assert round(rows[0]["slightly_toxic_pct"], 2) == 33.33
    assert rows[0]["excluded_or_pending"] == 1
    assert rows[1]["highly_toxic_pct"] is None
    assert calculer(depot, run) == rows
    assert depot.db.site_statistics.count_documents({}) == 2
    assert depot.db.predictions.count_documents({"origin": "batch"}) == 3

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from conftest import FauxService

from analyse_toxicite.pipeline import analyser, collecter_source


def test_source_isolee_et_plafond(depot, source):
    html = Path("tests/fixtures/article.html").read_text(encoding="utf-8")
    date = datetime(2026, 11, 11, tzinfo=UTC)
    run = {"_id": "r", "start": date - timedelta(days=3), "end": date, "limit": 1}

    class Client:
        async def obtenir(self, url, _source):
            if url.endswith("rss"):
                text = (
                    '<rss version="2.0"><channel><title>Flux</title>'
                    "<item><link>https://example.com/fail</link></item>"
                    "<item><link>https://example.com/a</link></item>"
                    "<item><link>https://example.com/a?utm_source=duplicate</link></item>"
                    "<item><link>https://example.com/b</link></item>"
                    "</channel></rss>"
                )
            elif url.endswith("fail"):
                raise httpx.ConnectError("panne isolée")
            else:
                text = html
            return httpx.Response(200, text=text, request=httpx.Request("GET", url))

    asyncio.run(collecter_source(source, run, depot, Client()))
    assert depot.db.run_articles.count_documents({"status": "collection_error"}) == 1
    assert depot.db.run_articles.count_documents({"status": "eligible"}) == 1
    assert depot.db.run_articles.count_documents({"status": "limit_reached"}) == 1
    count = depot.db.articles.count_documents({})
    asyncio.run(collecter_source(source, run, depot, Client()))
    assert depot.db.articles.count_documents({}) == count


def test_reprise_batch_et_snapshot(depot):
    run = {"_id": "r"}
    depot.db.pipeline_runs.insert_one(run)
    article = {
        "canonical_url": "https://example.com/a",
        "site": "test",
        "text": "Version originale",
        "content_hash": "original",
        "article_id": "a",
    }
    depot.observation("r", article["canonical_url"], "test", status="eligible", article=article)
    service = FauxService()
    assert analyser(depot, run, service)["scored"] == 1
    assert analyser(depot, run, service) == {}
    depot.article({**article, "text": "Version modifiée", "content_hash": "modifie"})
    assert depot.db.predictions.find_one({"origin": "batch"})["text"] == "Version originale"

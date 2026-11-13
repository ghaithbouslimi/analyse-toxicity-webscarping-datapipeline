import asyncio
from collections import Counter
from datetime import UTC, datetime

from analyse_toxicite.collecte.decouverte import decouvrir
from analyse_toxicite.collecte.extraction import extraire
from analyse_toxicite.collecte.telechargement import Telechargeur


async def collecter_source(source, run, depot, client):
    run_id = run["_id"]
    candidates, errors = await decouvrir(source, client)
    for error in errors:
        depot.observation(
            run_id, error["url"], source["id"], status="discovery_error", detail=error
        )
    retained = {
        item["article"]["canonical_url"]
        for item in depot.db.run_articles.find(
            {"run_id": run_id, "site": source["id"], "status": {"$in": ["eligible", "scored"]}}
        )
    }
    for candidate in candidates:
        url = candidate["url"]
        previous = depot.db.run_articles.find_one({"run_id": run_id, "url": url})
        if previous and previous["status"] in {"eligible", "scored"}:
            continue
        if len(retained) >= run["limit"]:
            depot.observation(run_id, url, source["id"], status="limit_reached")
            continue
        date = candidate["published_at"]
        if date and not run["start"] <= date <= run["end"]:
            depot.observation(run_id, url, source["id"], status="outside_window")
            continue
        try:
            response = await client.obtenir(url, source)
            article = extraire(response.text, str(response.url), source, date)
            status = article["status"]
            date = article["published_at"]
            if status == "eligible" and not run["start"] <= date <= run["end"]:
                status = "outside_window"
            if article["canonical_url"] in retained:
                status = "duplicate_canonical"
            article_id = depot.article(article)
            article["article_id"] = article_id
            depot.observation(
                run_id,
                url,
                source["id"],
                status=status,
                article=article,
                http_status=response.status_code,
            )
            if status == "eligible":
                retained.add(article["canonical_url"])
        except Exception as exc:
            depot.observation(
                run_id,
                url,
                source["id"],
                status="collection_error",
                error=f"{type(exc).__name__}: {exc}",
            )


async def collecter(settings, depot, run):
    async with Telechargeur(settings) as client:
        results = await asyncio.gather(
            *[collecter_source(source, run, depot, client) for source in run["sources"]],
            return_exceptions=True,
        )
    failures = [str(result) for result in results if isinstance(result, Exception)]
    depot.db.pipeline_runs.update_one(
        {"_id": run["_id"]},
        {
            "$set": {
                "status": "collection_errors" if failures else "collected",
                "collection_errors": failures,
                "collected_at": datetime.now(UTC),
            }
        },
    )
    if failures:
        raise RuntimeError(f"Sources en échec: {failures}")


def analyser(depot, run, service):
    pending = list(
        depot.db.run_articles.find(
            {"run_id": run["_id"], "status": {"$in": ["eligible", "inference_error"]}}
        )
    )
    if not pending:
        return {}
    service.charger()
    # Une seule configuration de scoring est autorisée dans un run.
    depot.db.pipeline_runs.update_one(
        {"_id": run["_id"], "scoring_hash": {"$exists": False}},
        {"$set": {"scoring_hash": service.config_hash, "model": service.config}},
    )
    current = depot.db.pipeline_runs.find_one({"_id": run["_id"]})
    if current["scoring_hash"] != service.config_hash:
        raise ValueError("Configuration différente: créer un nouveau run")
    counts = Counter()
    for observation in pending:
        try:
            result = service.predire(observation["article"]["text"])
            key = depot.prediction_batch(run["_id"], observation["article"], result)
            depot.db.run_articles.update_one(
                {"_id": observation["_id"]},
                {
                    "$set": {
                        "status": "scored",
                        "prediction_id": key,
                    },
                    "$unset": {"error": ""},
                },
            )
            counts["scored"] += 1
        except Exception as exc:
            depot.db.run_articles.update_one(
                {"_id": observation["_id"]},
                {
                    "$set": {
                        "status": "inference_error",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                },
            )
            counts["errors"] += 1
    depot.db.pipeline_runs.update_one(
        {"_id": run["_id"]},
        {
            "$set": {
                "status": "analysis_errors" if counts["errors"] else "analysed",
                "analysed_at": datetime.now(UTC),
            }
        },
    )
    return dict(counts)

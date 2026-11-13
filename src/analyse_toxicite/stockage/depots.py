import hashlib
from datetime import UTC, datetime
from uuid import uuid4

from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError


def identifiant(*values):
    return hashlib.sha256("\0".join(values).encode()).hexdigest()


class Depots:
    def __init__(self, database):
        self.db = database

    def indexer(self):
        self.db.articles.create_index("canonical_url", unique=True)
        self.db.predictions.create_index(
            "batch_key", unique=True, partialFilterExpression={"origin": "batch"}
        )
        self.db.predictions.create_index([("run_id", ASCENDING), ("site", ASCENDING)])
        self.db.run_articles.create_index([("run_id", 1), ("site", 1), ("status", 1)])
        self.db.site_statistics.create_index([("run_id", 1), ("site", 1)], unique=True)

    def article(self, article):
        article_id = identifiant(article["canonical_url"])
        self.db.articles.update_one({"_id": article_id}, {"$set": article}, upsert=True)
        return article_id

    def observation(self, run_id, url, site, **values):
        key = identifiant(run_id, site, url)
        self.db.run_articles.update_one(
            {"_id": key},
            {"$set": {"run_id": run_id, "url": url, "site": site, **values}},
            upsert=True,
        )

    def prediction_batch(self, run_id, article, result):
        # Une version de texte et une configuration distinctes gardent leur historique.
        key = identifiant(
            run_id, article["canonical_url"], article["content_hash"], result["config_hash"]
        )
        document = {
            "_id": key,
            "batch_key": key,
            "origin": "batch",
            "run_id": run_id,
            "article_id": article["article_id"],
            "site": article["site"],
            "source_url": article["canonical_url"],
            "text": article["text"],
            "content_hash": article["content_hash"],
            **result,
        }
        try:
            self.db.predictions.update_one({"_id": key}, {"$setOnInsert": document}, upsert=True)
        except DuplicateKeyError:
            # Deux processus ont calculé la même clé, le premier résultat reste la référence.
            pass
        return key

    def prediction_api(self, text, source_url, result):
        key = str(uuid4())
        self.db.predictions.insert_one(
            {
                "_id": key,
                "origin": "api",
                "text": text,
                "source_url": source_url,
                "content_hash": hashlib.sha256(text.encode()).hexdigest(),
                **result,
            }
        )
        return key

    def nouveau_run(self, settings, sources, start, end, limit):
        key = str(uuid4())
        self.db.pipeline_runs.insert_one(
            {
                "_id": key,
                "created_at": datetime.now(UTC),
                "start": start,
                "end": end,
                "limit": limit,
                "sources": sources,
                "collection_config": {
                    "delay": settings.request_delay_seconds,
                    "attempts": settings.http_max_attempts,
                    "timeout": settings.http_timeout_seconds,
                },
                "status": "collecting",
            }
        )
        return key

"""Contrôle réel du serveur déjà démarré et lecture indépendante de MongoDB.

Exemple : python scripts/verifier_api_url.py --url https://exemple.fr/article
Les appels réussis créent des prédictions persistantes, sans modifier les runs batch.
"""

import argparse
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

from analyse_toxicite.parametres import Parametres
from analyse_toxicite.stockage.connexion import connecter


def verifier(base_url, urls):
    settings = Parametres()
    report = {"checked_at": datetime.now(UTC).isoformat(), "base_url": base_url, "articles": []}
    with connecter(settings) as mongo, httpx.Client(timeout=180, trust_env=False) as client:
        db = mongo[settings.mongodb_database]
        statistics = list(db.site_statistics.find().sort("_id"))
        batch_count = db.predictions.count_documents({"origin": "batch"})
        for path in ("/health", "/ready", "/docs"):
            response = client.get(base_url + path)
            response.raise_for_status()
            assert response.status_code == 200, path
        for url in urls:
            start = time.perf_counter()
            response = client.post(base_url + "/predict", json={"source_url": url})
            assert response.status_code == 200, f"{url} : {response.status_code} {response.text}"
            result = response.json()
            article = result["article"]
            prediction = db.predictions.find_one({"_id": result["prediction_id"]})
            assert prediction is not None, "Prédiction absente de MongoDB"
            stored_article = db.articles.find_one({"_id": article["article_id"]})
            assert stored_article is not None, "Article absent de MongoDB"
            text = prediction["text"]
            content_hash = hashlib.sha256(text.encode()).hexdigest()
            assert text == stored_article["text"] and text != url
            assert len(text) == article["text_characters"] >= 300
            assert prediction["content_hash"] == article["content_hash"] == content_hash
            assert article["http_status"] == stored_article["http_status"] == 200
            assert prediction["article"]["article_id"] == article["article_id"]
            assert prediction["toxicity_score"] == result["toxicity_score"]
            assert result["model"]["revision"] == settings.model_revision
            report["articles"].append(
                {
                    "url": url,
                    "api_http_status": response.status_code,
                    "source_http_status": article["http_status"],
                    "prediction_id": result["prediction_id"],
                    "article_id": article["article_id"],
                    "title": article["title"],
                    "characters": len(text),
                    "content_hash": content_hash,
                    "extraction_status": article["status"],
                    "toxicity_score": result["toxicity_score"],
                    "category": result["category"],
                    "passages": len(result["passage_scores"]),
                    "request_seconds": round(time.perf_counter() - start, 3),
                    "mongo_verified": True,
                }
            )
        response = client.post(
            base_url + "/predict",
            json={"text": "Bonjour, merci pour votre aide.", "source_url": urls[0]},
        )
        assert response.status_code == 200
        result = response.json()
        assert "article" not in result
        assert db.predictions.find_one({"_id": result["prediction_id"]})["text"] == (
            "Bonjour, merci pour votre aide."
        )
        report["text_mode_verified"] = True
        count = db.predictions.count_documents({})
        for payload in ({}, {"source_url": "http://127.0.0.1:27019/"}):
            assert client.post(base_url + "/predict", json=payload).status_code == 422
        assert db.predictions.count_documents({}) == count
        report["invalid_requests"] = {
            "checked": 2,
            "http_status": 422,
            "no_prediction_created": True,
        }
        assert db.predictions.count_documents({"origin": "batch"}) == batch_count
        assert list(db.site_statistics.find().sort("_id")) == statistics
        report["batch_statistics_unchanged"] = True
        assert client.get(base_url + "/ready").status_code == 200
        report["passed"] = True
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", action="append", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8005")
    parser.add_argument("--output", type=Path, default=Path("rapports/verification_api_url.json"))
    args = parser.parse_args()
    report = verifier(args.base_url.rstrip("/"), args.url)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

"""Contrôle HTTP avec le modèle et MongoDB réels, sans doubles de test."""

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
import psutil

from analyse_toxicite.parametres import Parametres
from analyse_toxicite.statistiques import calculer
from analyse_toxicite.stockage.connexion import connecter
from analyse_toxicite.stockage.depots import Depots


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    settings = Parametres()
    started = datetime.now(UTC)
    base_url = f"http://127.0.0.1:{settings.api_port}"
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", settings.api_port))

    with connecter(settings) as client:
        depot = Depots(client[settings.mongodb_database])
        run = depot.db.pipeline_runs.find_one({"_id": args.run_id})
        if run is None:
            raise ValueError("Run inconnu")
        snapshots = list(depot.db.predictions.find({"origin": "batch", "run_id": args.run_id}))
        if not snapshots:
            raise ValueError("Le run doit contenir des prédictions batch")
        batch = min(snapshots, key=lambda item: len(item["text"]))
        before_statistics = calculer(depot, run)
        previous_ids = set(depot.db.predictions.distinct("_id", {"origin": "api"}))
        server_version = client.server_info()["version"]
        environment = dict(
            os.environ, HF_HUB_OFFLINE="1", OPENBLAS_NUM_THREADS="1", PYTHONFAULTHANDLER="1"
        )
        Path("rapports").mkdir(exist_ok=True)
        with Path("rapports-api.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                [sys.executable, "-u", "-m", "analyse_toxicite.cli", "servir"],
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            checks = []
            try:
                deadline = time.monotonic() + 90
                with httpx.Client(base_url=base_url, timeout=120, trust_env=False) as http:
                    while time.monotonic() < deadline:
                        if process.poll() is not None:
                            raise RuntimeError(
                                f"Serveur arrêté (code {process.returncode}), "
                                "consulter rapports-api.log"
                            )
                        try:
                            ready = http.get("/ready", timeout=1)
                            if ready.status_code == 200:
                                break
                        except httpx.TransportError:
                            pass
                        time.sleep(0.5)
                    else:
                        raise RuntimeError("API indisponible après 90 secondes")
                    for endpoint in ("/health", "/ready", "/docs"):
                        response = http.get(endpoint)
                        assert response.status_code == 200, response.text
                        checks.append({"endpoint": endpoint, "status": 200})
                    samples = [
                        ("Tu es un imbécile et je te déteste.", None),
                        (
                            "The new video game will be released next month.",
                            "http://127.0.0.1:9/metadata",
                        ),
                        (batch["text"], batch["source_url"]),
                    ]
                    created_ids = []
                    for text, url in samples:
                        response = http.post("/predict", json={"text": text, "source_url": url})
                        assert response.status_code == 200, response.text
                        result = response.json()
                        # Une connexion indépendante relit le document acquitté par l'API.
                        with connecter(settings) as reader:
                            stored = reader[settings.mongodb_database].predictions.find_one(
                                {"_id": result["prediction_id"]}
                            )
                        assert stored is not None
                        assert stored["text"] == text and stored["origin"] == "api"
                        assert stored["source_url"] == url
                        assert stored["content_hash"] == hashlib.sha256(text.encode()).hexdigest()
                        for field in (
                            "prediction",
                            "toxicity_score",
                            "confidence_score",
                            "category",
                            "config_hash",
                            "model",
                            "passage_scores",
                        ):
                            assert stored[field] == result[field], field
                        date = datetime.fromisoformat(result["date"])
                        assert stored["date"] == date.replace(
                            microsecond=(date.microsecond // 1000) * 1000
                        )
                        created_ids.append(result["prediction_id"])
                        checks.append(
                            {"endpoint": "/predict", "status": 200, "persisted": True, **result}
                        )
                    assert checks[-1]["config_hash"] == batch["config_hash"]
                    assert checks[-1]["toxicity_score"] == batch["toxicity_score"]
                    before_invalid = depot.db.predictions.count_documents({"origin": "api"})
                    invalid_samples = [
                        {},
                        {"text": ""},
                        {"text": "   "},
                        {"text": "x" * (settings.max_text_characters + 1)},
                        {"text": "Bonjour", "source_url": "file:///test"},
                    ]
                    for payload in invalid_samples:
                        response = http.post("/predict", json=payload)
                        assert response.status_code == 422, response.text
                        checks.append(
                            {
                                "endpoint": "/predict",
                                "status": 422,
                                "characters": len(payload.get("text", "")),
                                "source_url": payload.get("source_url"),
                            }
                        )
                    assert before_invalid == depot.db.predictions.count_documents({"origin": "api"})
                assert before_statistics == calculer(depot, run)
                after_ids = set(depot.db.predictions.distinct("_id", {"origin": "api"}))
                assert previous_ids <= after_ids
                assert len(set(created_ids)) == 3
            finally:
                # Le lanceur venv Windows peut avoir créé un processus Python enfant.
                try:
                    parent = psutil.Process(process.pid)
                    owned = parent.children(recursive=True) + [parent]
                except psutil.NoSuchProcess:
                    owned = []
                for child in owned:
                    try:
                        child.terminate()
                    except psutil.NoSuchProcess:
                        pass
                _, alive = psutil.wait_procs(owned, timeout=10)
                for child in alive:
                    child.kill()
                process.wait(timeout=10)
        report = {
            "started_at": started.isoformat(),
            "finished_at": datetime.now(UTC).isoformat(),
            "run_id": args.run_id,
            "base_url": base_url,
            "mongodb_database": settings.mongodb_database,
            "mongodb_version": server_version,
            "checks": checks,
            "batch_api_equal": True,
            "statistics_unchanged": True,
            "existing_api_predictions_preserved": True,
            "invalid_requests_not_persisted": True,
            "batch_predictions": len(snapshots),
            "api_predictions_before": len(previous_ids),
            "api_predictions_created": len(created_ids),
            "api_predictions": len(after_ids),
            "created_prediction_ids": created_ids,
            "temporary_server_stopped": True,
        }
    Path("rapports/verification_api.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "checks"}, ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()

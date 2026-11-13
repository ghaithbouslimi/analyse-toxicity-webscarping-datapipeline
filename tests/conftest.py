from datetime import UTC, datetime

import mongomock
import pytest

from analyse_toxicite.parametres import Parametres
from analyse_toxicite.stockage.depots import Depots


@pytest.fixture
def settings():
    return Parametres(
        _env_file=None,
        model_revision="a" * 40,
        request_delay_seconds=0.001,
    )


@pytest.fixture
def depot():
    result = Depots(mongomock.MongoClient(tz_aware=True).test)
    result.indexer()
    return result


@pytest.fixture
def source():
    return {
        "id": "test",
        "domain": "example.com",
        "language": "fr",
        "start_url": "https://example.com/",
        "feed_url": "https://example.com/rss",
    }


class FauxService:
    """Double explicite, aucune inférence réelle dans les tests unitaires."""

    model = object()
    config_hash = "test-config"
    config = {"revision": "a" * 40}

    def charger(self):
        pass

    def predire(self, text):
        return {
            "prediction": "non_toxique",
            "toxicity_score": 0.1,
            "confidence_score": 0.9,
            "category": "non_toxique",
            "date": datetime.now(UTC),
            "model": self.config,
            "config_hash": self.config_hash,
            "passage_scores": [0.1],
            "token_count": len(text),
            "calibrated": False,
            "latency_seconds": 0,
            "rss_mb": 0,
        }

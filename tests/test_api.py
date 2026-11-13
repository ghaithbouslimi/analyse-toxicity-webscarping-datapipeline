from unittest.mock import MagicMock, Mock

import pytest
from conftest import FauxService
from fastapi.testclient import TestClient
from pymongo.errors import AutoReconnect, ServerSelectionTimeoutError

from analyse_toxicite.api import application
from analyse_toxicite.api.application import creer_application


def test_persistence_et_validation(settings, depot):
    with TestClient(creer_application(settings, depot, FauxService())) as client:
        assert client.get("/ready").status_code == 200
        response = client.post(
            "/predict", json={"text": "Bonjour", "source_url": "https://example.com"}
        )
        assert response.status_code == 200
        key = response.json()["prediction_id"]
        assert depot.db.predictions.find_one({"_id": key})["text"] == "Bonjour"
        assert client.post("/predict", json={"text": "   "}).status_code == 422
        assert client.post("/predict", json={"text": "x" * 20001}).status_code == 422
        assert (
            client.post("/predict", json={"text": "x", "source_url": "file:///x"}).status_code
            == 422
        )
        assert client.post("/predict", json={"text": "x" * 20000}).status_code == 200


def test_erreur_mongodb_interdit_succes(settings, depot, monkeypatch):
    def fail(*args):
        raise AutoReconnect("panne simulée")

    monkeypatch.setattr(depot, "prediction_api", fail)
    with TestClient(creer_application(settings, depot, FauxService())) as client:
        assert client.post("/predict", json={"text": "Bonjour"}).status_code == 503


def test_erreur_inference(settings, depot):
    class ServiceEnPanne(FauxService):
        def predire(self, text):
            raise RuntimeError("panne simulée")

    with TestClient(creer_application(settings, depot, ServiceEnPanne())) as client:
        assert client.post("/predict", json={"text": "Bonjour"}).status_code == 503
        assert depot.db.predictions.count_documents({}) == 0


def test_mongodb_absent_interrompt_demarrage(settings, monkeypatch):
    connecter = Mock(side_effect=ServerSelectionTimeoutError("MongoDB arrêté"))
    monkeypatch.setattr(application, "connecter", connecter)
    service = FauxService()
    service.charger = Mock()
    with pytest.raises(ServerSelectionTimeoutError, match="MongoDB arrêté"):
        with TestClient(creer_application(settings, service=service)):
            pytest.fail("Le démarrage devait échouer")
    service.charger.assert_not_called()


def test_modele_en_echec_ferme_connexion(settings, depot, monkeypatch):
    client = MagicMock()
    client.__getitem__.return_value = depot.db
    monkeypatch.setattr(application, "connecter", Mock(return_value=client))
    service = FauxService()
    service.charger = Mock(side_effect=RuntimeError("Modèle indisponible"))
    with pytest.raises(RuntimeError, match="Modèle indisponible"):
        with TestClient(creer_application(settings, service=service)):
            pytest.fail("Le démarrage devait échouer")
    client.close.assert_called_once_with()

import threading
from concurrent.futures import ThreadPoolExecutor

from conftest import FauxService
from fastapi.testclient import TestClient

from analyse_toxicite.api.application import creer_application


def test_surcharge_refusee_sans_prediction_et_place_liberee(settings, depot):
    settings.api_max_pending_requests = 1
    entered = threading.Event()
    release = threading.Event()

    class ServiceLent(FauxService):
        def predire(self, text):
            entered.set()
            assert release.wait(timeout=10)
            return super().predire(text)

    with TestClient(creer_application(settings, depot, ServiceLent())) as client:
        with ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(client.post, "/predict", json={"text": "Bonjour"})
            try:
                assert entered.wait(timeout=5)
                rejected = client.post("/predict", json={"text": "Autre demande"})
                assert rejected.status_code == 429
                assert rejected.headers["Retry-After"] == "5"
                assert depot.db.predictions.count_documents({}) == 0
            finally:
                release.set()
            assert first.result(timeout=5).status_code == 200
        assert client.post("/predict", json={"text": "Après libération"}).status_code == 200
        assert depot.db.predictions.count_documents({}) == 2


def test_erreur_inference_libere_la_place(settings, depot):
    settings.api_max_pending_requests = 1

    class ServiceIntermittent(FauxService):
        calls = 0

        def predire(self, text):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("Erreur simulée")
            return super().predire(text)

    with TestClient(creer_application(settings, depot, ServiceIntermittent())) as client:
        assert client.post("/predict", json={"text": "Premier appel"}).status_code == 503
        assert client.post("/predict", json={"text": "Deuxième appel"}).status_code == 200
        assert depot.db.predictions.count_documents({}) == 1

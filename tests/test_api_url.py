import hashlib
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest
from conftest import FauxService
from fastapi.testclient import TestClient
from pymongo.errors import AutoReconnect

from analyse_toxicite.api.application import creer_application
from analyse_toxicite.collecte.telechargement import Telechargeur

URL = "https://example.com/article"
HTML = Path("tests/fixtures/article.html").read_text(encoding="utf-8")


def application_url(settings, depot, html=HTML, status=200, mime="text/html", robots=""):
    calls = []

    def handle(request):
        calls.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=f"User-agent: *\nDisallow: {robots}")
        return httpx.Response(status, text=html, headers={"Content-Type": mime})

    downloader = Telechargeur(settings, transport=httpx.MockTransport(handle), public_only=True)
    service = FauxService()
    service.predire = Mock(wraps=service.predire)
    app = creer_application(settings, depot, service, downloader)
    return app, service, calls


def test_url_extrait_analyse_et_persiste_le_texte(settings, depot):
    app, service, calls = application_url(settings, depot)
    with TestClient(app) as client:
        response = client.post("/predict", json={"source_url": URL})
        assert response.status_code == 200
        data = response.json()
        article = data["article"]
        assert article["title"] == "Un article de test"
        assert article["http_status"] == 200
        assert article["status"] == "eligible"
        assert article["canonical_url"] == URL
        stored = depot.db.predictions.find_one({"_id": data["prediction_id"]})
        assert "Le conseil municipal" in stored["text"]
        assert stored["text"] != URL
        assert len(stored["text"]) == article["text_characters"]
        assert stored["content_hash"] == hashlib.sha256(stored["text"].encode()).hexdigest()
        assert stored["article"]["article_id"] == article["article_id"]
        assert depot.db.articles.find_one({"_id": article["article_id"]})["text"] == stored["text"]
        service.predire.assert_called_once_with(stored["text"])
        assert calls == ["https://example.com/robots.txt", URL]
        assert depot.db.site_statistics.count_documents({}) == 0
        examples = client.get("/openapi.json").json()["paths"]["/predict"]["post"]["requestBody"][
            "content"
        ]["application/json"]["examples"]
        assert "text" not in examples["article_url"]["value"]


def test_texte_prioritaire_conserve_url_comme_metadonnee(settings, depot):
    app, service, calls = application_url(settings, depot)
    with TestClient(app) as client:
        response = client.post(
            "/predict", json={"text": "Bonjour", "source_url": "http://localhost:8005/article"}
        )
        assert response.status_code == 200
        assert "article" not in response.json()
        service.predire.assert_called_once_with("Bonjour")
        assert calls == []
        assert depot.db.articles.count_documents({}) == 0


@pytest.mark.parametrize("payload", [{}, {"text": None}, {"source_url": URL, "text": "   "}])
def test_entree_vide_refusee(settings, depot, payload):
    app, service, calls = application_url(settings, depot)
    with TestClient(app) as client:
        assert client.post("/predict", json=payload).status_code == 422
        service.predire.assert_not_called()
        assert calls == []


@pytest.mark.parametrize(
    ("options", "status", "message"),
    [
        ({"status": 403}, 502, "HTTP 403"),
        ({"mime": "application/pdf"}, 422, "HTML"),
        ({"robots": "/article"}, 422, "robots.txt interdit"),
        ({"html": "<html><h1>Page bloquée</h1></html>"}, 422, "Extraction incomplète"),
        (
            {
                "html": HTML.replace(
                    "</head>",
                    '<script type="application/ld+json">'
                    '{"isAccessibleForFree":false}</script></head>',
                )
            },
            422,
            "Article payant",
        ),
    ],
)
def test_article_inexploitable_non_analyse(settings, depot, options, status, message):
    app, service, _ = application_url(settings, depot, **options)
    with TestClient(app) as client:
        response = client.post("/predict", json={"source_url": URL})
        assert response.status_code == status
        assert message in response.json()["detail"]
        service.predire.assert_not_called()
        assert depot.db.predictions.count_documents({}) == 0
        assert depot.db.articles.count_documents({}) == 0


def test_article_trop_long_non_tronque(settings, depot):
    settings.max_text_characters = 300
    app, service, _ = application_url(settings, depot)
    with TestClient(app) as client:
        response = client.post("/predict", json={"source_url": URL})
        assert response.status_code == 422
        assert "Maximum 300" in response.json()["detail"]
        service.predire.assert_not_called()
        assert depot.db.predictions.count_documents({}) == 0


def test_url_locale_non_telechargee(settings, depot):
    app, service, calls = application_url(settings, depot)
    with TestClient(app) as client:
        response = client.post("/predict", json={"source_url": "http://127.0.0.1:8005/"})
        assert response.status_code == 422
        assert calls == []
        service.predire.assert_not_called()


@pytest.mark.parametrize(
    ("error", "status"), [(httpx.ReadTimeout("délai"), 504), (httpx.ConnectError("panne"), 502)]
)
def test_erreurs_reseau_explicites(settings, depot, error, status):
    settings.http_max_attempts = 1

    def handle(request):
        raise error

    downloader = Telechargeur(settings, transport=httpx.MockTransport(handle), public_only=True)
    service = FauxService()
    service.predire = Mock()
    with TestClient(creer_application(settings, depot, service, downloader)) as client:
        assert client.post("/predict", json={"source_url": URL}).status_code == status
        service.predire.assert_not_called()
        assert depot.db.predictions.count_documents({}) == 0


def test_date_absente_autorisee_pour_url_directe(settings, depot):
    html = HTML.replace(
        '<meta property="article:published_time" content="2026-11-10T10:00:00Z">', ""
    )
    app, _, _ = application_url(settings, depot, html=html)
    with TestClient(app) as client:
        response = client.post("/predict", json={"source_url": URL, "text": None})
        assert response.status_code == 200
        assert response.json()["article"]["status"] == "unknown_date"


@pytest.mark.parametrize("operation", ["article", "prediction_api"])
def test_echec_persistance_article_interdit_succes(settings, depot, monkeypatch, operation):
    monkeypatch.setattr(depot, operation, Mock(side_effect=AutoReconnect("MongoDB indisponible")))
    app, _, _ = application_url(settings, depot)
    with TestClient(app) as client:
        assert client.post("/predict", json={"source_url": URL}).status_code == 503
        assert depot.db.predictions.count_documents({}) == 0

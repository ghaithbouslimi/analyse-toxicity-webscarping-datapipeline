import asyncio
from pathlib import Path

import httpx
import pytest

from analyse_toxicite.collecte.decouverte import decouvrir, dedupliquer
from analyse_toxicite.collecte.extraction import extraire
from analyse_toxicite.collecte.telechargement import (
    AccesRefuse,
    Telechargeur,
    delai_retry,
    url_valide,
)


def test_deduplication_avant_plafond(source):
    urls = [
        "https://example.com/a?utm_source=x",
        "https://example.com/a#fragment",
        "https://example.com/b",
        "https://evil.com/a",
    ]
    assert len(dedupliquer([{"url": url} for url in urls], source)) == 2


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/a",
        "https://example.com.evil.com/a",
        "https://example.com:9000/a",
        "https://user@example.com/a",
        "file:///etc/passwd",
    ],
)
def test_domaines_interdits(url, source):
    with pytest.raises(AccesRefuse):
        url_valide(url, source)


def test_extraction_fixture(source):
    html = Path("tests/fixtures/article.html").read_text(encoding="utf-8")
    article = extraire(html, "https://example.com/article", source)
    assert article["status"] == "eligible"
    assert len(article["content_hash"]) == 64
    assert article["published_at"].isoformat() == "2026-11-10T10:00:00+00:00"
    restricted = html.replace(
        "</head>",
        '<script type="application/ld+json">{"isAccessibleForFree":false}</script></head>',
    )
    assert extraire(restricted, "https://example.com/article", source)["status"] == "paywall"


def test_retry_after():
    assert delai_retry("12", 0) == 12
    assert delai_retry(None, 2) == 4


def test_retries_robots_et_redirection(settings, source):
    attempts = []

    def handle(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /secret")
        attempts.append(request.url.path)
        if request.url.path == "/redirect":
            return httpx.Response(302, headers={"Location": "http://127.0.0.1/"})
        if len(attempts) < 3:
            return httpx.Response(503, headers={"Retry-After": "0"})
        return httpx.Response(200, text="ok")

    async def exercise():
        async with Telechargeur(settings, transport=httpx.MockTransport(handle)) as client:
            assert (await client.obtenir("https://example.com/a", source)).text == "ok"
            with pytest.raises(AccesRefuse):
                await client.obtenir("https://example.com/secret", source)
            with pytest.raises(AccesRefuse):
                await client.obtenir("https://example.com/redirect", source)

    asyncio.run(exercise())
    assert attempts.count("/a") == 3
    assert "/secret" not in attempts


def test_erreur_flux_fallback(source):
    class Client:
        async def obtenir(self, url, source):
            if url.endswith("rss"):
                raise httpx.ConnectError("panne simulée")
            return httpx.Response(
                200,
                text='<article><a href="/article">Titre</a></article>',
                request=httpx.Request("GET", url),
            )

    candidates, errors = asyncio.run(decouvrir(source, Client()))
    assert len(candidates) == 1
    assert errors[0]["stage"] == "feed"

import asyncio
import socket

import httpx
import pytest

from analyse_toxicite.collecte.telechargement import AccesRefuse, Telechargeur
from analyse_toxicite.collecte.transport_public import TransportPublic, url_publique


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://10.0.0.1/",
        "http://169.254.169.254/",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
        "http://localhost/",
        "http://machine.local/",
        "https://user:secret@example.com/",
        "https://example.com:27019/",
        "file:///etc/passwd",
        "http://224.0.0.1/",
        "http://[64:ff9b::7f00:1]/",
    ],
)
def test_url_non_publique_refusee(url):
    with pytest.raises(AccesRefuse):
        url_publique(url)


def dns_simule(monkeypatch, addresses):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443)) for address in addresses
        ],
    )


def test_dns_epingle_avec_host_et_sni_originaux(monkeypatch):
    dns_simule(monkeypatch, ["1.1.1.1", "64:ff9b::101:101"])
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(200, text="ok")

    async def exercise():
        async with httpx.AsyncClient(
            transport=TransportPublic(httpx.MockTransport(handle))
        ) as client:
            response = await client.get("https://news.example/article")
            assert str(response.url) == "https://news.example/article"

    asyncio.run(exercise())
    assert requests[0].url.host == "1.1.1.1"
    assert requests[0].headers["Host"] == "news.example"
    assert requests[0].extensions["sni_hostname"] == "news.example"


def test_dns_melange_public_prive_refuse_avant_connexion(monkeypatch):
    dns_simule(monkeypatch, ["1.1.1.1", "127.0.0.1"])
    calls = []

    async def exercise():
        async with httpx.AsyncClient(
            transport=TransportPublic(httpx.MockTransport(lambda request: calls.append(request)))
        ) as client:
            with pytest.raises(AccesRefuse):
                await client.get("https://news.example/article")

    asyncio.run(exercise())
    assert calls == []


@pytest.mark.parametrize("destination", ["https://other.example/article", "http://127.0.0.1/"])
def test_redirections_publiques_et_privees(settings, monkeypatch, destination):
    dns_simule(monkeypatch, ["1.1.1.1"])
    calls = []

    def handle(request):
        calls.append((request.headers["Host"], request.url.path))
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow:")
        if request.headers["Host"] == "news.example":
            return httpx.Response(302, headers={"Location": destination})
        return httpx.Response(200, text="Article public")

    async def exercise():
        transport = TransportPublic(httpx.MockTransport(handle))
        async with Telechargeur(settings, transport=transport, public_only=True) as client:
            if "127.0.0.1" in destination:
                with pytest.raises(AccesRefuse):
                    await client.obtenir("https://news.example/article", None)
            else:
                response = await client.obtenir("https://news.example/article", None)
                assert str(response.url) == destination
                assert response.text == "Article public"

    asyncio.run(exercise())
    assert ("127.0.0.1", "/") not in calls
    if "other.example" in destination:
        assert ("other.example", "/robots.txt") in calls

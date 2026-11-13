import asyncio
import time
from collections import defaultdict
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx

USER_AGENT = "AnalyseToxiciteEtude/0.1"
MAX_RESPONSE_BYTES = 8_000_000


class AccesRefuse(Exception):
    """Accès refusé, redirection externe ou réponse HTTP inexploitable."""


def url_valide(url, source, verifier_chemin=True):
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    domain = source["domain"]
    allowed = host == domain or host == "www." + domain
    prefix = source.get("path_prefix", "/") if verifier_chemin else "/"
    if (
        parts.scheme not in {"https", "http"}
        or not allowed
        or parts.username
        or parts.password
        or parts.port not in {None, 80, 443}
        or not parts.path.startswith(prefix)
    ):
        raise AccesRefuse(f"URL hors du périmètre autorisé: {url}")
    # Les paramètres de suivi sont retirés. Les paramètres fonctionnels sont préservés.
    from urllib.parse import parse_qsl, urlencode

    query = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(parts.query)
            if not key.startswith("utm_") and key not in {"fbclid", "gclid"}
        ]
    )
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path or "/", query, ""))


def delai_retry(value, attempt):
    try:
        return max(0.0, float(value))
    except (ValueError, TypeError):
        try:
            date = parsedate_to_datetime(value)
            return max(0.0, (date - datetime.now(UTC)).total_seconds())
        except (ValueError, TypeError, OverflowError):
            return min(2**attempt, 30)


class Telechargeur:
    def __init__(self, settings, transport=None, public_only=False):
        self.settings = settings
        self.public_only = public_only
        if public_only and transport is None:
            from analyse_toxicite.collecte.transport_public import TransportPublic

            transport = TransportPublic()
        self.client = httpx.AsyncClient(
            timeout=settings.http_timeout_seconds,
            follow_redirects=False,
            headers={"User-Agent": USER_AGENT},
            transport=transport,
            trust_env=not public_only,
        )
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_requests)
        self.locks = defaultdict(asyncio.Lock)
        self.last = defaultdict(float)
        self.robots = {}
        self.robot_locks = defaultdict(asyncio.Lock)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.client.aclose()

    def _valider(self, url, source):
        if self.public_only:
            from analyse_toxicite.collecte.transport_public import url_publique

            return url_publique(url)
        return url_valide(url, source, verifier_chemin=False)

    async def _requete(self, url, source):
        self._valider(url, source)
        host = urlsplit(url).netloc
        async with self.locks[host]:
            pause = self.settings.request_delay_seconds - (time.monotonic() - self.last[host])
            await asyncio.sleep(max(0, pause))
            async with self.semaphore:
                try:
                    async with self.client.stream("GET", url) as response:
                        chunks = []
                        length = 0
                        async for chunk in response.aiter_bytes():
                            length += len(chunk)
                            if length > MAX_RESPONSE_BYTES:
                                raise AccesRefuse("Réponse trop volumineuse")
                            chunks.append(chunk)
                        headers = dict(response.headers)
                        headers.pop("content-encoding", None)
                        headers.pop("content-length", None)
                        return httpx.Response(
                            response.status_code,
                            headers=headers,
                            content=b"".join(chunks),
                            request=response.request,
                        )
                finally:
                    self.last[host] = time.monotonic()

    async def _autoriser(self, url, source):
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        async with self.robot_locks[origin]:
            if origin not in self.robots:
                response = await self._obtenir(origin + "/robots.txt", source, robots=False)
                parser = RobotFileParser()
                if response.status_code == 404:
                    parser.parse([])
                elif response.is_success:
                    parser.parse(response.text.splitlines())
                else:
                    raise AccesRefuse(f"robots.txt inaccessible: {response.status_code}")
                self.robots[origin] = parser
            parser = self.robots[origin]
        if not parser.can_fetch(USER_AGENT, url):
            raise AccesRefuse(f"robots.txt interdit: {url}")
        delay = parser.crawl_delay(USER_AGENT) or parser.crawl_delay("*")
        if delay:
            self.settings.request_delay_seconds = max(self.settings.request_delay_seconds, delay)

    async def _obtenir(self, url, source, robots=True):
        for _redirect in range(6):
            url = self._valider(url, source)
            if robots:
                await self._autoriser(url, source)
            for attempt in range(self.settings.http_max_attempts):
                try:
                    response = await self._requete(url, source)
                except httpx.TransportError:
                    if attempt + 1 == self.settings.http_max_attempts:
                        raise
                    await asyncio.sleep(delai_retry(None, attempt))
                    continue
                if response.status_code not in {429, 500, 502, 503, 504}:
                    break
                if attempt + 1 < self.settings.http_max_attempts:
                    delay = delai_retry(response.headers.get("Retry-After"), attempt)
                    if delay > 60:
                        raise AccesRefuse(f"Retry-After de {delay}s: requête différée")
                    await asyncio.sleep(delay)
            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise AccesRefuse("Redirection sans destination")
                url = urljoin(url, location)
                continue
            return response
        raise AccesRefuse("Trop de redirections")

    async def obtenir(self, url, source):
        response = await self._obtenir(url, source)
        response.raise_for_status()
        return response

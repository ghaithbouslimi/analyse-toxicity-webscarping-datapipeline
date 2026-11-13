"""Transport des URL soumises à l'API, limité aux adresses Internet publiques."""

import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit

import httpx

from analyse_toxicite.collecte.telechargement import AccesRefuse, url_valide


def adresse_publique(value):
    address = ipaddress.ip_address(value)
    if address.version == 6 and address in ipaddress.ip_network("64:ff9b::/96"):
        # Le DNS peut fournir une adresse NAT64 ; vérifier aussi l'IPv4 qu'elle contient.
        return adresse_publique(str(ipaddress.IPv4Address(int(address) & 0xFFFFFFFF)))
    return (
        address.is_global
        and not address.is_multicast
        and not address.is_reserved
        and not getattr(address, "is_site_local", False)
        and not getattr(address, "ipv4_mapped", None)
        and not getattr(address, "sixtofour", None)
        and not getattr(address, "teredo", None)
    )


def url_publique(url):
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        if not host or "%" in host:
            raise ValueError("Hôte invalide")
        if parts.username is not None or parts.password is not None:
            raise AccesRefuse("Les URL contenant des identifiants ne sont pas acceptées")
        normalized = url_valide(url, {"domain": host})
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            if "." not in host or host.rstrip(".").endswith((".localhost", ".local")):
                raise AccesRefuse("L’URL doit désigner un site Internet public") from None
        else:
            if not adresse_publique(str(address)):
                raise AccesRefuse("Les adresses locales ou privées sont interdites")
        return normalized
    except ValueError as exc:
        raise AccesRefuse("URL HTTP(S) invalide") from exc


class TransportPublic(httpx.AsyncBaseTransport):
    def __init__(self, transport=None):
        # Une connexion TLS ne doit pas être réutilisée entre deux domaines partageant une IP.
        self.transport = transport or httpx.AsyncHTTPTransport(
            trust_env=False, limits=httpx.Limits(max_keepalive_connections=0)
        )

    async def handle_async_request(self, request):
        url_publique(str(request.url))
        host = request.url.host
        port = request.url.port or (443 if request.url.scheme == "https" else 80)
        timeout = request.extensions.get("timeout", {}).get("connect", 20)
        try:
            records = await asyncio.wait_for(
                asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM),
                timeout=timeout,
            )
        except TimeoutError as exc:
            raise httpx.ConnectTimeout("Résolution DNS trop lente", request=request) from exc
        except OSError as exc:
            raise httpx.ConnectError("Résolution DNS impossible", request=request) from exc
        addresses = list(dict.fromkeys(record[4][0] for record in records))
        if not addresses or any(not adresse_publique(address) for address in addresses):
            raise AccesRefuse("Le domaine ne résout pas exclusivement vers Internet public")
        addresses.sort(key=lambda address: ":" in address)
        for index, address in enumerate(addresses[:2]):
            headers = request.headers.copy()
            headers["Host"] = request.url.netloc.decode("ascii")
            pinned = httpx.Request(
                request.method,
                request.url.copy_with(host=address),
                headers=headers,
                content=request.content,
                extensions={**request.extensions, "sni_hostname": host},
            )
            try:
                # L'adresse validée est utilisée directement : aucune seconde résolution DNS.
                return await self.transport.handle_async_request(pinned)
            except (httpx.ConnectError, httpx.ConnectTimeout):
                if index + 1 == min(2, len(addresses)):
                    raise

    async def aclose(self):
        await self.transport.aclose()

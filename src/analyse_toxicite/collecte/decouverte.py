from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin

import feedparser
from bs4 import BeautifulSoup

from analyse_toxicite.collecte.telechargement import AccesRefuse, url_valide


def date_utc(value):
    if not value:
        return None
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            date = parsedate_to_datetime(value)
        except (ValueError, TypeError):
            return None
    return date.replace(tzinfo=date.tzinfo or UTC).astimezone(UTC)


def dedupliquer(candidates, source):
    seen = set()
    result = []
    for candidate in candidates:
        try:
            url = url_valide(candidate["url"], source)
        except (AccesRefuse, ValueError):
            continue
        if url not in seen:
            seen.add(url)
            result.append({**candidate, "url": url})
    return result


async def decouvrir(source, client):
    errors = []
    candidates = []
    try:
        response = await client.obtenir(source["feed_url"], source)
        feed = feedparser.parse(response.content)
        if not feed.entries:
            raise ValueError("Flux sans entrée exploitable")
        candidates = [
            {"url": entry.link, "published_at": date_utc(entry.get("published"))}
            for entry in feed.entries
            if entry.get("link")
        ]
    except Exception as exc:
        errors.append({"url": source["feed_url"], "stage": "feed", "error": str(exc)})
    if not candidates:
        try:
            response = await client.obtenir(source["start_url"], source)
            soup = BeautifulSoup(response.text, "html.parser")
            candidates = [
                {"url": urljoin(str(response.url), anchor["href"]), "published_at": None}
                for anchor in soup.select("article a[href], h2 a[href], h3 a[href]")
            ]
            if not candidates:
                raise ValueError("Aucun lien article/h2/h3 trouvé")
        except Exception as exc:
            errors.append({"url": source["start_url"], "stage": "homepage", "error": str(exc)})
    return dedupliquer(candidates, source), errors

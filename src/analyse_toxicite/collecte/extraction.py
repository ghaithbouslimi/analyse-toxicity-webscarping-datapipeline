import hashlib
import json
from datetime import UTC, datetime
from urllib.parse import urljoin

import trafilatura
from bs4 import BeautifulSoup

from analyse_toxicite.collecte.decouverte import date_utc
from analyse_toxicite.collecte.telechargement import url_valide


def objets_json(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from objets_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from objets_json(child)


def extraire(html, url, source, date_flux=None):
    soup = BeautifulSoup(html, "html.parser")
    canonical = soup.select_one('link[rel="canonical"]')
    canonical_url = url_valide(
        urljoin(url, canonical.get("href", url)) if canonical else url, source
    )
    doc = trafilatura.extract(
        html,
        url=url,
        output_format="json",
        with_metadata=True,
        include_comments=False,
        include_tables=False,
        date_extraction_params={"original_date": True, "extensive_search": False},
    )
    data = json.loads(doc) if doc else {}
    text = data.get("text", "").strip()
    title = data.get("title") or (soup.h1.get_text(" ", strip=True) if soup.h1 else "")
    published = None
    restricted = False
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            objects = list(objets_json(json.loads(script.string or script.get_text())))
        except (ValueError, TypeError):
            continue
        for obj in objects:
            if obj.get("isAccessibleForFree") in {False, "false", "False"}:
                restricted = True
            if obj.get("datePublished"):
                published = date_utc(obj["datePublished"]) or published
    meta = soup.select_one('meta[property="article:published_time"]')
    if meta:
        published = date_utc(meta.get("content")) or published
    # La date publiée explicite et celle du flux précèdent la date heuristique.
    published = published or date_flux or date_utc(data.get("date"))
    status = "eligible"
    if restricted:
        status = "paywall"
    elif not title or len(text) < 300:
        status = "incomplete"
    elif published is None:
        status = "unknown_date"
    return {
        "canonical_url": canonical_url,
        "source_url": url,
        "title": title,
        "text": text,
        "site": source["id"],
        "language": source["language"],
        "published_at": published,
        "collected_at": datetime.now(UTC),
        "content_hash": hashlib.sha256(text.encode()).hexdigest(),
        "status": status,
    }

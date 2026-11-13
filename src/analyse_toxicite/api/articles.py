import asyncio
from urllib.parse import urlsplit

from analyse_toxicite.collecte.extraction import extraire
from analyse_toxicite.collecte.telechargement import AccesRefuse
from analyse_toxicite.parametres import charger_sources


class LecteurArticle:
    def __init__(self, settings, telechargeur):
        self.telechargeur = telechargeur
        self.sources = charger_sources(settings.sources_file)

    async def lire(self, url):
        response = await self.telechargeur.obtenir(url, None)
        if response.status_code != 200:
            raise AccesRefuse(
                f"Le site n’a pas renvoyé un article HTTP 200 ({response.status_code})"
            )
        mime = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if mime not in {"text/html", "application/xhtml+xml"}:
            raise AccesRefuse("L’URL doit renvoyer une page HTML d’article")
        final_url = str(response.url)
        host = urlsplit(final_url).hostname
        source = next(
            (
                {**item, "path_prefix": "/"}
                for item in self.sources
                if host in {item["domain"], "www." + item["domain"]}
            ),
            {"id": host, "domain": host, "language": "und"},
        )
        try:
            article = await asyncio.to_thread(extraire, response.text, final_url, source)
        except (ValueError, TypeError) as exc:
            raise AccesRefuse("Le contenu HTML de l’article est inexploitable") from exc
        if article["status"] == "paywall":
            raise AccesRefuse("Article payant : le texte intégral public n’est pas disponible")
        if article["status"] == "incomplete":
            raise AccesRefuse(
                "Extraction incomplète : titre absent ou texte de moins de 300 caractères"
            )
        # Une analyse à la demande n'impose pas la fenêtre temporelle de la collecte batch.
        article["http_status"] = response.status_code
        article["requested_url"] = url
        return article

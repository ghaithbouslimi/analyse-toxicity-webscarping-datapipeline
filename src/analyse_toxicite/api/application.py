import asyncio
import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from analyse_toxicite.api.articles import LecteurArticle
from analyse_toxicite.api.routes import router
from analyse_toxicite.collecte.telechargement import Telechargeur
from analyse_toxicite.journalisation import configurer
from analyse_toxicite.parametres import Parametres
from analyse_toxicite.prediction.service import ServicePrediction
from analyse_toxicite.stockage.connexion import connecter
from analyse_toxicite.stockage.depots import Depots


def creer_application(settings=None, depot=None, service=None, telechargeur=None):
    settings = settings or Parametres()
    service = service or ServicePrediction(settings)

    @asynccontextmanager
    async def lifespan(app):
        configurer(settings.log_level)
        client = None
        downloader = None
        app.state.startup_error = None
        app.state.settings = settings
        app.state.service = service
        app.state.request_slots = threading.BoundedSemaphore(settings.api_max_pending_requests)
        try:
            if depot is None:
                client = await asyncio.to_thread(connecter, settings)
                active_depot = Depots(client[settings.mongodb_database])
            else:
                active_depot = depot
            await asyncio.to_thread(active_depot.indexer)
            app.state.depot = active_depot
            await asyncio.to_thread(service.charger)
            downloader = telechargeur or Telechargeur(settings, public_only=True)
            app.state.lecteur = LecteurArticle(settings, downloader)
        except Exception as exc:
            app.state.startup_error = str(exc)
            logging.getLogger(__name__).exception("Initialisation échouée")
            if client is not None:
                client.close()
            if downloader is not None:
                await downloader.__aexit__()
            raise
        try:
            yield
        finally:
            await downloader.__aexit__()
            if client is not None:
                client.close()

    app = FastAPI(
        title="Analyse de toxicité",
        version="0.1.0",
        lifespan=lifespan,
        description=(
            "Analyse de toxicité non calibrée. Fournir uniquement source_url pour extraire "
            "et analyser un article public, ou text pour analyser un texte directement."
        ),
    )
    app.include_router(router)
    return app

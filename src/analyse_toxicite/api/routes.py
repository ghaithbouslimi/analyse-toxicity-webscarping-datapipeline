import asyncio
import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pymongo.errors import PyMongoError

from analyse_toxicite.api.schemas import PredictionEntree, PredictionSortie
from analyse_toxicite.collecte.telechargement import AccesRefuse

router = APIRouter()
logger = logging.getLogger(__name__)


async def limiter_charge(request: Request):
    slots = request.app.state.request_slots
    if not slots.acquire(blocking=False):
        raise HTTPException(
            429,
            "Capacité d’analyse atteinte ; réessayer dans quelques secondes",
            headers={"Retry-After": "5"},
        )
    try:
        yield
    finally:
        slots.release()


@router.get("/health", tags=["santé"])
def sante():
    return {"status": "alive"}


@router.get("/ready", tags=["santé"])
def disponibilite(request: Request):
    state = request.app.state
    if state.startup_error or state.service.model is None:
        raise HTTPException(503, "Initialisation incomplète, consulter les journaux")
    try:
        state.depot.db.command("ping")
    except PyMongoError as exc:
        raise HTTPException(503, "MongoDB indisponible") from exc
    return {"status": "ready", "model_revision": state.settings.model_revision}


@router.post(
    "/predict",
    response_model=PredictionSortie,
    response_model_exclude_none=True,
    tags=["prédiction"],
    dependencies=[Depends(limiter_charge)],
    responses={429: {"description": "Capacité atteinte ; réessayer après Retry-After secondes"}},
)
async def predire(
    request: Request,
    entree: Annotated[
        PredictionEntree,
        Body(
            openapi_examples={
                "article_url": {
                    "summary": "Article par URL (extraction automatique)",
                    "value": {"source_url": "https://www.bbc.com/news/articles/c9kgjj206nzpo"},
                },
                "texte": {
                    "summary": "Texte fourni directement",
                    "value": {"text": "Le conseil municipal présente son budget annuel."},
                },
            }
        ),
    ],
):
    """Analyse un article par URL ou un texte et enregistre le résultat dans MongoDB.

    Pour l'extraction automatique, fournir uniquement source_url (ou text: null).
    Si text est fourni, il est analysé et source_url reste une métadonnée.
    Les pages payantes, bloquées ou insuffisamment extraites ne sont pas analysées.
    """
    state = request.app.state
    if state.startup_error:
        raise HTTPException(503, "Service en cours d’initialisation ou indisponible")
    text = entree.text
    source_url = str(entree.source_url) if entree.source_url else None
    article = None
    if text is None:
        try:
            article = await state.lecteur.lire(source_url)
        except AccesRefuse as exc:
            raise HTTPException(422, str(exc)) from exc
        except httpx.TimeoutException as exc:
            raise HTTPException(504, "Le site n’a pas répondu dans le délai autorisé") from exc
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                502,
                f"Téléchargement impossible : le site a renvoyé HTTP {exc.response.status_code}",
            ) from exc
        except httpx.RequestError as exc:
            raise HTTPException(502, "Connexion au site impossible") from exc
        text = article["text"]
    if len(text) > state.settings.max_text_characters:
        raise HTTPException(
            422, f"Maximum {state.settings.max_text_characters} caractères à analyser"
        )
    try:
        result = await asyncio.to_thread(state.service.predire, text)
    except Exception as exc:
        logger.exception("Échec d’inférence")
        raise HTTPException(503, "Inférence indisponible") from exc
    try:
        if article is not None:
            article_id = await asyncio.to_thread(state.depot.article, article)
            result = {
                **result,
                "article": {
                    **{key: value for key, value in article.items() if key != "text"},
                    "article_id": article_id,
                    "text_characters": len(text),
                },
            }
        key = await asyncio.to_thread(state.depot.prediction_api, text, source_url, result)
    except PyMongoError as exc:
        logger.exception("Échec de persistance")
        raise HTTPException(503, "Prédiction non confirmée en base") from exc
    return {"prediction_id": key, **result}

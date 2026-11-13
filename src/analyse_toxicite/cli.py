import argparse
import asyncio
import faulthandler
import json
import socket
from datetime import UTC, datetime, timedelta
from pathlib import Path

from analyse_toxicite.journalisation import configurer
from analyse_toxicite.parametres import Parametres, charger_sources
from analyse_toxicite.pipeline import analyser, collecter
from analyse_toxicite.prediction.service import ServicePrediction
from analyse_toxicite.statistiques import calculer, exporter
from analyse_toxicite.stockage.connexion import connecter
from analyse_toxicite.stockage.depots import Depots


def main():
    parser = argparse.ArgumentParser(description="Pipeline de toxicité de presse")
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("collecter", help="Créer ou reprendre une collecte")
    collect.add_argument("--run-id", help="Reprendre la même période et les mêmes paramètres")
    collect.add_argument("--sites", nargs="+", help="Identifiants des sources du pilote")
    collect.add_argument("--limit", type=int)
    collect.add_argument("--end", help="Fin UTC ISO 8601, par défaut maintenant")
    for name in ("analyser", "rapport", "etat"):
        sub = commands.add_parser(name)
        sub.add_argument("--run-id", required=True)
        if name == "rapport":
            sub.add_argument("--output")
    commands.add_parser("telecharger-modele")
    benchmark = commands.add_parser("verifier-modele")
    benchmark.add_argument("--output", default="rapports/verification_modele.json")
    commands.add_parser("servir")
    args = parser.parse_args()
    settings = Parametres()
    configurer(settings.log_level)
    if args.command == "servir":
        import uvicorn

        faulthandler.enable()
        family = socket.AF_INET6 if ":" in settings.api_host else socket.AF_INET
        try:
            with socket.socket(family) as probe:
                probe.bind((settings.api_host, settings.api_port))
        except OSError as exc:
            parser.exit(
                1,
                f"Impossible de démarrer l’API sur {settings.api_host}:{settings.api_port}. "
                f"Le port est indisponible ({exc}). "
                f"Si l’API est déjà lancée, ouvrir http://localhost:{settings.api_port}/docs. "
                "Pour choisir un autre port, définir API_PORT dans PowerShell ou .env.\n",
            )
        uvicorn.run(
            "analyse_toxicite.api.application:creer_application",
            factory=True,
            host=settings.api_host,
            port=settings.api_port,
            workers=1,
        )
        return
    if args.command in {"telecharger-modele", "verifier-modele"}:
        service = ServicePrediction(settings)
        service.charger()
        if args.command == "verifier-modele":
            samples = [
                ("fr_neutre", "Le conseil municipal présente son budget annuel."),
                ("en_neutre", "The new video game will be released next month."),
                ("fr_insulte", "Tu es un imbécile et je te déteste."),
                ("en_insulte", "You are a disgusting idiot and I hate you."),
                (
                    "fr_citation",
                    "Le témoin rapporte l’insulte « tu es un imbécile » devant le tribunal.",
                ),
                ("fr_long", "Le conseil municipal présente son budget annuel. " * 300),
            ]
            results = [
                {"sample": key, "text": text, **service.predire(text)} for key, text in samples
            ]
            path = Path(args.output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "load_metrics": service.load_metrics,
                        "results": results,
                    },
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                ),
                encoding="utf-8",
            )
        print(json.dumps(service.load_metrics))
        return
    with connecter(settings) as client:
        depot = Depots(client[settings.mongodb_database])
        depot.indexer()
        if args.command == "collecter" and not args.run_id:
            sources = charger_sources(settings.sources_file)
            if args.sites:
                unknown = set(args.sites) - {source["id"] for source in sources}
                if unknown:
                    parser.error(f"Sources inconnues: {unknown}")
                sources = [source for source in sources if source["id"] in args.sites]
            end = datetime.now(UTC)
            if args.end:
                end = datetime.fromisoformat(args.end.replace("Z", "+00:00"))
                if end.tzinfo is None:
                    parser.error("--end doit inclure un fuseau horaire")
                end = end.astimezone(UTC)
            limit = args.limit if args.limit is not None else settings.max_articles_per_site
            if limit <= 0:
                parser.error("--limit doit être positif")
            args.run_id = depot.nouveau_run(
                settings, sources, end - timedelta(days=settings.collection_window_days), end, limit
            )
        run = depot.db.pipeline_runs.find_one({"_id": args.run_id})
        if run is None:
            parser.error("Run inconnu")
        print(f"RUN_ID={run['_id']}", flush=True)
        if args.command == "collecter":
            if args.run_id and run.get("scoring_hash"):
                parser.error("La collecte est figée après le début de l’analyse")
            asyncio.run(collecter(settings, depot, run))
        elif args.command == "analyser":
            print(json.dumps(analyser(depot, run, ServicePrediction(settings))))
        elif args.command == "rapport":
            output = args.output or f"rapports/{run['_id']}"
            exporter(calculer(depot, run), output)
            print(output)
        elif args.command == "etat":
            print(json.dumps(run, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()

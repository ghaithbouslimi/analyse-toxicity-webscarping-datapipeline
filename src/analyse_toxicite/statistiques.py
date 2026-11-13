import csv
import json
import os
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path


def calculer(depot, run):
    rows = []
    for source in run["sources"]:
        observations = list(
            depot.db.run_articles.find({"run_id": run["_id"], "site": source["id"]})
        )
        statuses = Counter(item["status"] for item in observations)
        ids = {item["prediction_id"] for item in observations if item["status"] == "scored"}
        # Les pointeurs des observations sélectionnent un unique snapshot par article du run.
        predictions = list(
            depot.db.predictions.find(
                {
                    "_id": {"$in": list(ids)},
                    "origin": "batch",
                    "run_id": run["_id"],
                    "site": source["id"],
                    "config_hash": run.get("scoring_hash"),
                }
            )
        )
        categories = Counter(item["category"] for item in predictions)
        total = len(predictions)
        light = categories["legerement_toxique"]
        high = categories["tres_toxique"]
        row = {
            "run_id": run["_id"],
            "site": source["id"],
            "observations": len(observations),
            "scored": total,
            "non_toxic": categories["non_toxique"],
            "slightly_toxic": light,
            "highly_toxic": high,
            "slightly_toxic_pct": 100 * light / total if total else None,
            "highly_toxic_pct": 100 * high / total if total else None,
            "toxic_pct": 100 * (light + high) / total if total else None,
            "excluded_or_pending": len(observations) - total,
            "coverage_pct": 100 * total / len(observations) if observations else None,
            "status": "calculé" if total else "données insuffisantes",
            "exclusions": {
                status: count for status, count in statuses.items() if status != "scored"
            },
            "model": run.get("model"),
            "period_start": run["start"],
            "period_end": run["end"],
        }
        depot.db.site_statistics.update_one(
            {"run_id": run["_id"], "site": source["id"]},
            {"$set": {**row, "computed_at": datetime.now(UTC)}},
            upsert=True,
        )
        rows.append(row)
    return rows


def exporter(rows, destination):
    cache = Path(".cache/matplotlib").resolve()
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path = Path(destination)
    path.mkdir(parents=True, exist_ok=True)
    fields = [key for key in rows[0] if key not in {"exclusions", "model"}]
    with (path / "toxicite_par_site.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    (path / "resultats.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    fig, ax = plt.subplots(figsize=(11, 6))
    for index, row in enumerate(rows):
        if not row["scored"]:
            ax.text(index, 3, "Données\ninsuffisantes", ha="center", fontsize=8, rotation=90)
            continue
        ax.bar(index, row["slightly_toxic_pct"], color="#dfaa49")
        ax.bar(index, row["highly_toxic_pct"], bottom=row["slightly_toxic_pct"], color="#bd453c")
        ax.text(index, min(96, row["toxic_pct"] + 2), f"n={row['scored']}", ha="center")
    from matplotlib.patches import Patch

    ax.legend(
        handles=[
            Patch(color="#dfaa49", label="Légèrement toxique (bande de score)"),
            Patch(color="#bd453c", label="Très toxique (bande de score)"),
        ],
        loc="upper right",
    )
    ax.set(
        ylim=(0, 110),
        ylabel="% des articles effectivement scorés",
        title=f"Toxicité par site — run {rows[0]['run_id'][:8]}",
    )
    ax.set_xticks(range(len(rows)), [row["site"] for row in rows], rotation=25)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path / "toxicite_par_site.png", dpi=160)
    plt.close(fig)
    ranked = sorted(
        [row for row in rows if row["scored"]], key=lambda row: row["toxic_pct"], reverse=True
    )
    if ranked:
        ranking = "\n".join(
            f"- {row['site']} — {row['toxic_pct']:.2f} %, n={row['scored']}" for row in ranked
        )
        interpretation = "Classement descriptif des sites observés sur ce run.\n\n" + ranking
    else:
        interpretation = "Données insuffisantes pour établir un classement des sites."
    text = (
        f"# Rapport du run {rows[0]['run_id']}\n\n"
        f"Période UTC du {rows[0]['period_start']} au {rows[0]['period_end']}.\n\n"
        + interpretation
        + "\n\nLes bandes de scores sont provisoires et non calibrées. Le maximum des passages "
        "favorise les textes longs et peut réagir aux citations. Les restrictions d’accès et "
        "l’échantillonnage limitent toute comparaison éditoriale ou généralisation.\n"
    )
    (path / "interpretation.md").write_text(text, encoding="utf-8")

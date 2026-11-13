"""Crée une archive de remise inférieure à 20 Mo, sans modèle, secrets ni environnements."""

import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 20_000_000
FILES = (
    "README.md",
    "Dockerfile",
    "compose.yaml",
    ".env.example",
    ".dockerignore",
    ".gitignore",
    ".gitattributes",
    "pyproject.toml",
    "uv.lock",
    "requirements.lock",
)
DIRECTORIES = ("src", "configuration", "tests", "scripts", "documentation", "rapports")
EXCLUDED_DIRECTORIES = {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".git"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "livraison/Ghaith_Bouslimi_Data_Engineer.zip"
    )
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT) or output.suffix.lower() != ".zip":
        parser.error("La destination doit être un fichier .zip dans le projet")
    payload = [ROOT / name for name in FILES]
    for directory in DIRECTORIES:
        folder = ROOT / directory
        if not folder.is_dir():
            parser.error(f"Dossier nécessaire absent : {directory}")
        for path in folder.rglob("*"):
            if (
                not path.is_file()
                or path.is_symlink()
                or EXCLUDED_DIRECTORIES.intersection(path.relative_to(ROOT).parts)
                or path.suffix.lower() in {".pyc", ".log", ".zip"}
                or path.name == ".env"
                or path.name.startswith(".env.")
                or (directory == "rapports" and path.name.startswith("articles"))
            ):
                continue
            if not path.resolve().is_relative_to(ROOT):
                parser.error(f"Fichier extérieur au projet : {path.relative_to(ROOT)}")
            payload.append(path)
    guide = ROOT / "documentation/guide_recruteur.md"
    for path in [*payload, guide]:
        if not path.is_file():
            parser.error(f"Fichier nécessaire absent : {path.relative_to(ROOT)}")
    manifest = {
        "created_at": datetime.now(UTC).isoformat(),
        "external_components": (
            "Modèle, dépendances et images téléchargés au premier démarrage. "
            "Données MongoDB créées dans un volume persistant."
        ),
        "files": [],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".zip.part", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            entries = [("00_GUIDE_RECRUTEUR.md", guide)] + [
                ("analyse-toxicite/" + path.relative_to(ROOT).as_posix(), path)
                for path in sorted(payload)
            ]
            for name, path in entries:
                content = path.read_bytes()
                archive.writestr(name, content)
                manifest["files"].append(
                    {"path": name, "sha256": hashlib.sha256(content).hexdigest()}
                )
            archive.writestr("MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        if temporary.stat().st_size >= MAX_BYTES:
            raise RuntimeError("L’archive dépasse la limite stricte de 20 Mo")
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() is not None:
                raise RuntimeError("L’archive ne passe pas le contrôle d’intégrité")
            expected = {item["path"] for item in manifest["files"]} | {"MANIFEST.json"}
            if set(archive.namelist()) != expected:
                raise RuntimeError("Le contenu de l’archive diffère du manifeste")
            for item in manifest["files"]:
                if hashlib.sha256(archive.read(item["path"])).hexdigest() != item["sha256"]:
                    raise RuntimeError(f"Empreinte incorrecte pour {item['path']}")
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    print(
        json.dumps(
            {
                "archive": str(output),
                "bytes": output.stat().st_size,
                "files": len(payload) + 2,
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            },
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()

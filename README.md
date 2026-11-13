# Analyse de toxicité de presse

Pipeline de collecte d’articles, analyse multilingue de toxicité et stockage MongoDB. Une API FastAPI permet d’analyser un texte ou l’URL d’un article depuis Swagger. Les résultats batch sont exportés en JSON, CSV et graphique.

L’API et le batch partagent les modules de collecte, de prédiction et de stockage. La conception du système, les parcours des données et l’arborescence commentée sont détaillés dans le document d’architecture. [Architecture et logique métier](documentation/architecture_et_logique_metier.md).

## Prérequis

- Docker Desktop sur Windows, démarré en mode conteneurs Linux, avec Docker Compose.
- Une connexion Internet pour télécharger les images, les dépendances et le modèle public d’environ 1,1 Go.
- Plusieurs Go de disque libre et suffisamment de mémoire pour Docker, le modèle et MongoDB.

Les commandes ci-dessous utilisent **PowerShell**, depuis le dossier contenant `compose.yaml`. Python et MongoDB sont fournis par les conteneurs ; aucune installation locale n’est nécessaire pour ce parcours.

## Première installation avec Docker

```powershell
# Créer la configuration sans écraser un fichier .env existant.
if (-not (Test-Path -LiteralPath .env)) { Copy-Item .env.example .env }

docker compose config --quiet
docker compose build api
docker compose up -d mongodb
docker compose run --rm --no-deps api toxicite telecharger-modele
docker compose up -d --wait --wait-timeout 300 api
```

Le téléchargement initial peut prendre plusieurs minutes. La commande `telecharger-modele` charge aussi le modèle pour vérifier sa compatibilité. Attendre que les deux services soient `healthy` :

```powershell
docker compose ps
Invoke-RestMethod http://localhost:8005/ready
```

La réponse attendue contient `"status": "ready"`. Ouvrir ensuite **[Swagger — http://localhost:8005/docs](http://localhost:8005/docs)**.

Les redémarrages réutilisent le modèle dans `cache_modeles` et les données dans `mongo_data`. Les rapports sont écrits dans le dossier local `rapports/`.

## Analyser un texte ou un article

Dans Swagger, ouvrir **POST /predict → Try it out**, saisir l’un des corps JSON suivants, puis cliquer sur **Execute**.

Texte fourni directement :

```json
{"text": "Le conseil municipal présente son budget annuel."}
```

Extraction et analyse automatiques d’un article :

```json
{"source_url": "https://www.bbc.com/news/articles/c9kgjj206nzpo"}
```

Pour le mode URL, omettre `text`. Si les deux champs sont fournis, le texte est analysé et l’URL reste une métadonnée. La réponse contient notamment `prediction_id`, `toxicity_score`, `category` et les informations de l’article extrait. Chaque réponse HTTP 200 suit l’enregistrement de la prédiction dans MongoDB.

Les pages payantes, les refus HTTP et les pages nécessitant JavaScript peuvent empêcher l’extraction. Les limites par défaut sont de 8 Mo décompressés par page et de 20 000 caractères à analyser. Les scores et les seuils de catégorie ne sont pas calibrés sur un corpus de presse annoté.

## Collecte batch et rapports

La collecte utilise une fenêtre de 14 jours et un plafond par défaut de 30 articles exploitables par site. Pour un essai limité à deux sources :

```powershell
# Arrêter l’API pour éviter de charger deux modèles pendant l’analyse batch.
docker compose stop api
docker compose run --rm api toxicite collecter --sites humanite france24 --limit 2

# Remplacer cette valeur par le RUN_ID affiché lors de la collecte.
$runId = 'IDENTIFIANT_DU_RUN'
docker compose run --rm api toxicite analyser --run-id $runId
docker compose run --rm api toxicite rapport --run-id $runId

docker compose up -d --wait --wait-timeout 300 api
```

Les exports se trouvent dans `rapports/<run_id>/` : `resultats.json`, `toxicite_par_site.csv`, `toxicite_par_site.png` et `interpretation.md`. Les prédictions API disposent de leur propre historique et sont exclues des statistiques batch. Les rapports livrés sont historiques ; une nouvelle installation crée ses propres runs.

## Configuration et exploitation

Les paramètres modifiables figurent dans `.env.example`. Compose fournit automatiquement à l’API l’adresse interne `mongodb://mongodb:27017` et le chemin du cache modèle.

| Paramètre | Valeur par défaut | Rôle |
| --- | --- | --- |
| `API_HOST_PORT` | `8005` | Port de l’API dans le navigateur |
| `API_PORT` | `8000` | Port interne du conteneur API |
| `MONGO_HOST_PORT` | `27018` | Port MongoDB fixe pour Compass et les commandes locales |
| `API_CPUS` / `API_MEMORY_LIMIT` | `1.0` / `2g` | Plafonds CPU et mémoire de l’API |
| `MONGO_CPUS` / `MONGO_MEMORY_LIMIT` | `0.5` / `512m` | Plafonds CPU et mémoire de MongoDB |
| `API_MAX_PENDING_REQUESTS` | `2` | Nombre maximal de demandes admises simultanément |
| `MODEL_CACHE_VOLUME` | `cache_modeles` | Volume du modèle ; accepte aussi un chemin hôte absolu |

L’inférence utilise float16, un thread et un seul calcul à la fois. Les plafonds des services s’ajoutent aux ressources nécessaires au moteur Docker. Une limite CPU plus basse peut allonger l’analyse. Les journaux sont limités à deux fichiers de 5 Mo par service.

Pour un conflit de port, modifier `API_HOST_PORT` dans `.env`, puis relancer `docker compose up -d --wait --wait-timeout 300 api`. Adapter ensuite l’adresse du navigateur. Modifier `MONGO_HOST_PORT` dans `.env` si le port 27018 est occupé, puis adapter aussi `MONGODB_URI` et la connexion Compass.

### MongoDB après un redémarrage du PC

MongoDB utilise le port hôte fixe `27018`. Dans Compass, enregistrer une connexion nommée `Analyse toxicité Docker` avec l’URI `mongodb://127.0.0.1:27018/analyse_toxicite` et la méthode d’authentification `None` pour cette démonstration locale.

Activer **Docker Desktop → Settings → General → Start Docker Desktop when you sign in**. La politique `restart: always` relance ensuite MongoDB au démarrage du moteur Docker. Après l’ouverture de session Windows, attendre que Docker soit démarré et que MongoDB soit `healthy`, puis cliquer sur **Connect** dans Compass.

Pour démarrer ou rétablir uniquement MongoDB manuellement :

```powershell
docker compose up -d --wait --wait-timeout 120 mongodb
```

`docker compose stop` conserve les conteneurs pour le prochain démarrage. Après `docker compose down`, qui supprime les conteneurs, la commande précédente les recrée en réutilisant les données du volume.

```powershell
# Démarrer une installation existante avec son cache.
docker compose up -d --wait --wait-timeout 300

# Consulter l’état, les journaux et la consommation.
docker compose ps
docker compose logs --tail 50 api mongodb
docker stats --no-stream

# Arrêter les services en conservant les données et le modèle.
docker compose stop
```

| Réponse ou problème | Action |
| --- | --- |
| `/ready` indisponible | Consulter les journaux et attendre la fin du chargement du modèle |
| HTTP 422 | Vérifier l’entrée, la taille du texte et le message d’extraction |
| HTTP 429 | Attendre le délai `Retry-After`, puis réessayer |
| HTTP 502 / 504 | Vérifier l’accès au site et sa réponse réseau |
| HTTP 503 | Consulter les journaux du modèle et de MongoDB |

## Validation et documentation

Le dernier contrôle comprend **67 tests réussis**, une construction Docker complète, des analyses BBC et France 24 avec persistance réelle et un redémarrage conservant les prédictions. Les tests unitaires utilisent principalement des simulations ; les rapports distinguent ces contrôles des essais réels.

Pour relancer les tests sur une installation de développement avec **uv 0.13.7** :

```powershell
uv sync --frozen --python 3.11
uv run --frozen pytest -q
```

- [Guide recruteur](documentation/guide_recruteur.md)
- [Architecture, logique métier et rôle des fichiers](documentation/architecture_et_logique_metier.md)
- [Matrice de validation et limites observées](documentation/validation.md)
- [Choix techniques et logique métier](documentation/choix_techniques.md)
- [Ressources et livraison de moins de 20 Mo](documentation/optimisation_ressources.md)
- [Vérification réelle de l’API Docker](rapports/verification_docker_optimise.json)

L’archive de remise contient le code, les tests, la configuration et les rapports. Le modèle, les dépendances et les images sont téléchargés au premier démarrage ; une connexion Internet est nécessaire.

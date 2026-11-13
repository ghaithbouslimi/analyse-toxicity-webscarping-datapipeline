# Guide d’installation et d’évaluation

Ce projet extrait des articles de presse, analyse leur toxicité avec un modèle multilingue et conserve les résultats dans MongoDB. Il propose une collecte batch et une API FastAPI utilisable depuis Swagger.

## Contenu de la livraison

L’archive contient les sources, tests, configurations, verrous de dépendances, instructions Docker et rapports de validation. Elle ne contient pas les environnements Python, images Docker, poids du modèle ou données MongoDB de la machine de réalisation. Ces composants sont installés ou téléchargés au premier démarrage. Une connexion Internet est donc nécessaire. Une livraison autonome hors ligne avec ce modèle ne tient pas dans 20 Mo.

Le modèle `unitary/multilingual-toxic-xlm-roberta` conserve la révision `4ad6f5c104d9ce813a1a2f33cac0c5b579ef6ee5`. Ses poids téléchargés représentent environ 1,1 Go, même si l’inférence utilise float16 en mémoire. Le verrou `uv.lock` fournit les versions des bibliothèques. Aucun compte Hugging Face n’est requis pour le modèle public utilisé.

## Démarrage Docker

Le parcours ci-dessous a été validé sous Windows avec PowerShell et Docker Desktop en mode conteneurs Linux. Installer puis démarrer Docker Desktop. Prévoir plusieurs Go de stockage disponibles et de la mémoire pour le moteur Docker, les bibliothèques et le modèle. La mémoire nécessaire inclut également celle de Docker Desktop et de Windows.

Sur Linux natif avec Docker Engine et Compose, adapter les commandes au shell utilisé et donner à l’UID `10001` du conteneur les droits d’écriture sur le dossier hôte `rapports/`. La reproduction sur Linux natif reste à vérifier.

Exécuter les commandes suivantes dans PowerShell depuis le dossier `analyse-toxicite` extrait de l’archive.

```powershell
if (-not (Test-Path -LiteralPath .env)) { Copy-Item .env.example .env }
docker compose config --quiet
docker compose build api
docker compose up -d mongodb
docker compose run --rm --no-deps api toxicite telecharger-modele
docker compose up -d --wait --wait-timeout 300 api
docker compose ps
docker compose logs --tail 50 api
```

Attendre la fin du téléchargement et du chargement. La commande de téléchargement charge également le modèle pour vérifier sa compatibilité. Les redémarrages réutilisent le volume `cache_modeles`. La révision du modèle est déjà définie dans l’image et dans `.env.example`.

Ouvrir `http://localhost:8005/ready` et vérifier que la réponse contient `"status": "ready"`. Ouvrir ensuite `http://localhost:8005/docs`. Le port 8005 est celui du navigateur. Compose connecte l’API à MongoDB sur le réseau interne `mongodb:27017`.

## Utilisation de l’API

Dans Swagger, ouvrir **POST /predict → Try it out**. Pour vérifier le modèle sans dépendre d’un site de presse, envoyer :

```json
{"text": "Le conseil municipal présente son budget annuel."}
```

Pour télécharger puis analyser un article, choisir l’exemple **Article par URL** et envoyer uniquement :

```json
{"source_url": "https://www.bbc.com/news/articles/c9kgjj206nzpo"}
```

Cliquer sur **Execute**. La réponse expose l’identifiant de prédiction, le score, la catégorie et les informations d’extraction. Avec `text` et `source_url` ensemble, le texte fourni est analysé et l’URL reste une métadonnée.

Chaque réponse HTTP 200 suit la persistance de la prédiction. Le texte exact analysé et son hash figurent dans `predictions`. L’article extrait figure également dans `articles`.

## Ressources et limites

Par défaut, l’API dispose d’un cœur CPU au maximum et de 2 Gio de RAM ; MongoDB d’un demi-cœur et de 512 Mio. L’inférence fonctionne en float16, avec un thread et un seul calcul à la fois. Deux demandes au maximum sont admises simultanément ; les suivantes reçoivent HTTP 429 avec `Retry-After: 5`. Une machine moins puissante ou un article plus long peut augmenter la durée de l’appel.

Les journaux Docker tournent sur deux fichiers de 5 Mo par service. Le modèle et MongoDB utilisent des volumes persistants. `MODEL_CACHE_VOLUME` peut désigner un chemin absolu sur un autre disque ; les images et volumes nommés suivent, eux, l’emplacement de stockage du moteur Docker.

Les restrictions robots, HTTP 403, paywalls et pages nécessitant JavaScript peuvent empêcher une analyse. Un HTTP 200 du site ne garantit pas une extraction complète. Les refus observés sur certaines sources sont décrits dans `documentation/validation.md` ; ajouter de l’espace disque ne lève pas ces restrictions.

HTTP 422 indique une entrée ou un article inexploitable ; HTTP 502 une erreur d’accès au site ; HTTP 504 un délai réseau dépassé ; HTTP 503 une indisponibilité du modèle ou de MongoDB. Les scores ne sont pas calibrés sur un corpus de presse annoté.

## Collecte batch et rapports

Les rapports livrés sont des résultats historiques. Une installation neuve crée sa propre base et ses propres identifiants de run.

La validation du 13 novembre 2026 comprend 67 tests, une construction Docker complète, deux analyses d’articles par URL avec persistance réelle, ainsi qu’un redémarrage de l’API conservant les prédictions. Voir `rapports/verification_docker_optimise.json`, `rapports/optimisation_ressources.json` et la matrice dans `documentation/validation.md`.

```powershell
docker compose stop api
docker compose run --rm api toxicite collecter --sites humanite france24 --limit 2
# Copier le RUN_ID affiché dans la variable suivante.
$runId = 'IDENTIFIANT_DU_RUN'
docker compose run --rm api toxicite analyser --run-id $runId
docker compose run --rm api toxicite rapport --run-id $runId
docker compose up -d --wait --wait-timeout 300 api
```

Les fichiers apparaissent dans `rapports/<run_id>/`. L’arrêt temporaire de l’API libère la mémoire de son modèle pendant l’analyse batch. La dernière commande rétablit le service et attend sa disponibilité.

## Diagnostic et arrêt

```powershell
docker compose ps
docker compose logs --tail 100 api mongodb
docker stats --no-stream
docker compose stop
```

`stop` conserve les conteneurs, les données et le modèle. MongoDB utilise `restart: always` et le port hôte défini par `MONGO_HOST_PORT`, initialement 27018. Pour retrouver cette connexion après ouverture de session Windows, activer **Docker Desktop → Settings → General → Start Docker Desktop when you sign in**, puis attendre que MongoDB soit `healthy`.

Dans Compass, enregistrer `mongodb://127.0.0.1:27018/analyse_toxicite` avec l’authentification `None`. Après un `docker compose down`, exécuter `docker compose up -d --wait --wait-timeout 120 mongodb` pour recréer le conteneur avec son volume existant. Pour un conflit de port API, changer `API_HOST_PORT` dans `.env`, puis relancer `docker compose up -d --wait --wait-timeout 300 api`.

Pour la machine de réalisation, le stockage Docker a été déplacé de C: vers D: depuis les réglages Docker Desktop. Ce chemin local n’est pas requis sur l’ordinateur du recruteur. Il utilise `.env.example` et ses propres volumes.

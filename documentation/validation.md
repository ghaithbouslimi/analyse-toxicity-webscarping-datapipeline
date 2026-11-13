# Bilan et matrice des exigences

Validation du 12 novembre 2026 sur Windows 11 Pro, Python 3.11.9, Docker 29.9.2 et Compose 5.6.1. La machine dispose d’environ 8 Go de RAM. Le Python système 3.14 a été complété par un environnement 3.11 propre au projet.

## Résultats réels

Le run complet est `4d717f8d-b1c7-4c5f-8cdb-93bcc13e374c`. Sa période va du **29 octobre 2026 à 16:53:27.979 UTC au 12 novembre 2026 à 16:53:27.979 UTC**. Le plafond de validation a été fixé à trois articles exploitables par site afin de limiter le coût du pilote CPU. Le plafond par défaut du programme reste 30.

| Site | Articles scorés | Observations et limites |
| --- | --- | --- |
| L’Humanité | 3 | Flux et extraction exploitables, 17 candidats au-delà du plafond |
| GameSpot | 0 | Flux accessible, 14 articles refusés en HTTP 403 et un candidat hors période |
| Marianne | 0 | Flux et page de départ refusés en HTTP 403 |
| Le Monde | 0 | 16 contenus extraits sous le seuil de qualité ou incomplets |
| France 24 | 3 | Flux et contenus exploitables, 21 candidats au-delà du plafond |
| France 3 régions | 0 | Flux proposé en HTTP 404 et aucun lien exploitable par le secours configuré |
| Mediacités | 0 | 10 contenus signalés payants dans les métadonnées |
| Le Point | 0 | robots.txt refusé en HTTP 403, accès suspendu par le collecteur |

Les six articles scorés restent sous 0,5. Les deux sites observés ont donc 0 % dans chacune des bandes légèrement et très toxiques. Les effectifs de trois articles par site limitent l’interprétation. Les six autres sites affichent « données insuffisantes ». Les refus et contenus exclus empêchent un classement global des huit sites.

Le CSV, le graphique inspecté visuellement et l’interprétation figurent dans `rapports/4d717f8d-b1c7-4c5f-8cdb-93bcc13e374c/`. Les huit lignes statistiques sont enregistrées dans `site_statistics`. La commande d’analyse a produit `{"scored": 6}`. Une relance terminée produit `{}` et conserve les six prédictions batch.

Le contrôle du modèle réel figure dans `rapports/verification_modele.json`. La révision figée est `4ad6f5c104d9ce813a1a2f33cac0c5b579ef6ee5`, en float16 sur CPU. Les six cas fonctionnels couvrent français, anglais, insultes, citation et texte long de 2 400 tokens découpé en cinq passages. Les mesures et les limites sont détaillées dans `choix_techniques.md`.

La vérification HTTP complète du **12 novembre 2026 de 20:13:34 à 20:14:10, heure de Paris**, soit de 19:13:34 à 19:14:10 UTC, est conservée dans `rapports/verification_api.json`. Elle utilise MongoDB Windows 8.0.16, le modèle réel en float16 et son cache hors ligne.

Trois appels ont retourné HTTP 200, avec une décision toxique sur une insulte française, une décision non toxique sur une phrase anglaise et l’analyse d’un snapshot du batch. Chaque identifiant retourné a été relu avec une connexion MongoDB indépendante. Les contrôles ont comparé le texte, l’URL, le hash du contenu, la décision, les scores, les passages, la configuration du modèle et la date à la précision milliseconde de MongoDB.

Les trois documents API antérieurs sont présents et trois nouveaux documents ont été ajoutés, portant l’historique API à **six prédictions**. Le score et le hash de configuration de l’article soumis à l’API sont identiques au batch. Les statistiques sont identiques avant et après les appels et portent toujours sur **six prédictions batch**. Les champs manquants, le texte vide, les espaces seuls, le dépassement de taille et une URL `file://` ont retourné HTTP 422, sans ajout en base. `/health`, `/ready` et `/docs` ont retourné HTTP 200. Le serveur temporaire et ses processus enfants ont été arrêtés après le contrôle.

Le contrôle se reproduit depuis la racine du projet dans un environnement de développement Python 3.11 installé avec les dépendances du projet et une base contenant le run historique indiqué. La commande suivante reprend le chemin d’environnement utilisé sur la machine de validation.

```powershell
.venv311\Scripts\python.exe scripts/verifier_api_reelle.py --run-id 4d717f8d-b1c7-4c5f-8cdb-93bcc13e374c
```

Le port `API_PORT` doit être libre et MongoDB doit être démarré. Chaque exécution réussie ajoute trois prédictions à l’historique API et régénère le rapport de vérification.

Le **13 novembre 2026 à 01:24:21, heure de Paris**, un contrôle de remise en service a validé `/ready`, `/docs` et `/predict` sur le port 8005. Une connexion MongoDB indépendante a retrouvé la prédiction `c5315441-dd67-4a5a-93b3-5fc2652b0a3c`. La base contient alors 34 documents d’articles et 13 prédictions, dont sept d’origine API. Ce contrôle utilise un thread CPU et le modèle en float16. Son résultat figure dans `rapports/verification_demarrage_local.json`.

La panne initiale de ce démarrage venait de MongoDB arrêté sur le port 27019. Le gestionnaire de démarrage capturait l’exception puis poursuivait jusqu’au `yield` du cycle de vie FastAPI. Le serveur HTTP annonçait ainsi `Application startup complete` avec les dépendances indisponibles. Le code propage désormais l’erreur d’initialisation et ferme les connexions créées. Le connecteur ferme également son client lorsque le `ping` échoue. Les six tests ciblés d’API et de connexion passent, dont trois tests de régression ajoutés pour ces cas. Ruff valide les fichiers modifiés.

Une relance du modèle avec deux threads a rencontré une violation d’accès native pendant la conversion des poids. La relance avec `TORCH_THREADS=1` a abouti et ce réglage est conservé dans `.env` pour l’environnement local. Le lien causal entre le nombre de threads et l’arrêt natif demande encore une investigation.

Le **13 novembre 2026 à partir de 02:15:51, heure de Paris**, le parcours automatique par URL a été vérifié sur le serveur local, avec le modèle réel et une lecture MongoDB indépendante. Le rapport est conservé dans `rapports/verification_api_url.json` et le contrôle est reproductible avec `scripts/verifier_api_url.py --url URL_ARTICLE` depuis la racine du projet, serveur déjà démarré. Chaque exécution ajoute une prédiction par URL et une prédiction de contrôle du mode texte.

| Article testé par URL seule | HTTP du site / API | Texte analysé | Score | Durée de l’appel |
| --- | --- | --- | --- | --- |
| BBC — UK cannot 'cherry pick' EU single market deal, says Barnier | 200 / 200 | 5 068 caractères, trois passages | 0,133179, non toxique | 36,796 s |
| France 24 — Afghanistan : des oliviers pour lutter contre la sécheresse | 200 / 200 | 535 caractères, un passage | 0,000419, non toxique | 4,536 s |

Pour ces deux appels, les identifiants, textes, hashes, longueurs, statuts HTTP et scores ont été comparés aux documents persistés. Le mode texte avec URL comme métadonnée reste fonctionnel. Une entrée vide et une URL locale ont retourné HTTP 422 sans créer de prédiction. Les statistiques batch et les six prédictions batch sont restées identiques. `/health`, `/ready` et `/docs` ont répondu HTTP 200 avant le contrôle et `/ready` a encore répondu HTTP 200 après les prédictions. Le serveur a été laissé démarré sur le port 8005.

La résolution DNS de BBC fournit ici une IPv4 et son équivalent IPv6 NAT64. Le contrôle de destination accepte ce préfixe NAT64 uniquement lorsque l’IPv4 contenue est publique. Les tests couvrent également le refus des destinations privées, le contrôle après redirection et la conservation des noms HTTP/TLS avec une IP épinglée. Une extraction dépassant 300 caractères et munie d’un titre peut néanmoins rester éditorialement partielle ; les sites JavaScript, restrictions robots et paywalls restent des limites observables.

## Matrice du sujet

| Exigence | Fichier ou résultat | État de validation |
| --- | --- | --- |
| Collecte des huit sites | `configuration/sources.yaml`, `collecte/`, journal `rapports-collecte.log` | Exécutée sur huit sources, six articles exploitables de deux sites |
| URL, titre, texte | `collecte/extraction.py`, collection `articles` | 34 extractions initiales avec statuts ; nouvel article BBC persisté par l’API |
| MongoDB | `stockage/`, collections de données et résultats | MongoDB réel Docker pour la collecte, Windows 8.0.16 pour l’analyse |
| Gestion des erreurs HTTP et parsing | `telechargement.py`, `decouverte.py`, `pipeline.py` | Refus réels conservés, erreurs isolées et gzip testés avec fixtures |
| Endpoint `/predict` | `api/`, `rapports/verification_api.json`, `rapports/verification_api_url.json` | Modes texte et URL vérifiés avec modèle réel ; BBC et France 24 HTTP 200 |
| Extraction automatique par URL dans Swagger | `api/articles.py`, `tests/test_api_url.py`, `collecte/transport_public.py` | URL seule → extraction → inférence → persistance vérifiées ; erreurs et destinations privées couvertes |
| Décision et score de confiance | `prediction/service.py` | Modèle réel vérifié, sigmoïde et frontières testées |
| Historique des prédictions API | `stockage/depots.py`, `tests/test_api_url.py`, rapports de vérification API | Prédictions texte et URL relues par connexion indépendante ; échecs d’écriture article et prédiction testés |
| Modularité, entrées, erreurs et OpenAPI | `api/`, `parametres.py` | Tests des limites et erreurs, documentation `/docs` disponible au démarrage |
| Pourcentages légèrement et très toxiques | `statistiques.py`, CSV à huit lignes | Calcul réel sur six prédictions batch |
| Tableau ou graphique | `toxicite_par_site.csv`, `toxicite_par_site.png` | Générés depuis MongoDB, graphique inspecté |
| Statistiques dans MongoDB | collection `site_statistics`, `rapports/verification_api.json` | Huit documents du run, upserts idempotents, résultats identiques après les nouveaux appels API |
| Interprétation et sites les plus toxiques | `interpretation.md` et présent bilan | Deux sites ex aequo sur l’échantillon, données insuffisantes ailleurs |
| Conteneur FastAPI | `Dockerfile`, `rapports/verification_docker_optimise.json` | Construction complète, démarrage, analyses par URL et persistance vérifiés dans Docker |
| Port configurable | `API_HOST_PORT`, `API_PORT`, `compose.yaml` | Configuration Compose et publication réelle sur 8005 validées ; changement vers un autre port non testé |
| Instructions Docker | `README.md` | Commandes alignées sur les points d’entrée implémentés |
| Explications et configuration | `README.md`, `choix_techniques.md`, `.env.example` | Livrés en français |

## Tests reproductibles

`pytest -q` a exécuté **67 tests avec succès** après l’ajout du mode URL et de la limite de charge. Les tests utilisent des doubles explicites pour MongoDB, le réseau et les prédictions API. Les tests de sigmoïde utilisent PyTorch avec des logits construits. Les scénarios couvrent la déduplication avant plafond, les domaines et redirections, robots.txt, retries, gzip, paywall, panne isolée, reprise batch, snapshots, limites d’entrées, panne d’écriture, catégories et dénominateur statistique. Le mode URL ajoute notamment des contrôles du texte réellement transmis au modèle, de la persistance, des erreurs réseau, des destinations privées, du DNS épinglé et de NAT64. Les tests de charge vérifient HTTP 429 sans inférence supplémentaire et la libération de la capacité après succès ou erreur.

`ruff check src tests` et `ruff format --check src tests` sont les contrôles de qualité. Le verrouillage a été généré par uv et vérifié. Un avertissement de dépréciation de Starlette concerne le transport `httpx` du client de test dans les versions résolues. Les contrôles de production utilisent HTTPX 0.28.1.

## Incidents observés et travail restant

Le premier chargement a révélé la dépendance `protobuf` du tokenizer. Elle a été ajoutée et le verrouillage régénéré. Un décodage gzip appliqué deux fois lors de la reconstruction d’une réponse HTTP a été corrigé et couvert par un test. Le chargement float32 a échoué sur une allocation de 768 Mo. Float16 et un passage par batch ont permis la validation CPU.

Le téléchargement du modèle a rencontré `OSError: [Errno 28] No space left on device` sur C:. Les ressources volumineuses ont été placées dans `D:\CodexDataEngineerCache`. `.venv311` est une jonction vers l’environnement sur D:. Le cache du modèle et les données de MongoDB Windows sont également sur D:. Les fichiers `.env` et ces données sont exclus de Git.

La commande `docker compose build api` a exécuté l’installation et les étapes de l’image, puis l’export a échoué avec `failed to extract layer ... read-only file system` et `Unavailable: error reading from server: EOF`. Le moteur Docker a aussi rencontré des erreurs HTTP 500 et un redémarrage normal a expiré. La configuration `docker compose config --quiet` a été validée. Le lancement propre de l’image API, son redémarrage avec cache et la modification du port hôte demandent une nouvelle validation après rétablissement des ressources Docker.

Ce constat décrit les premiers essais. Le **13 novembre 2026**, après déplacement du disque Docker de C: vers D:, la construction complète et l’export de l’image ont réussi. Compose a démarré MongoDB et l’API avec leurs plafonds de ressources. Les deux services sont devenus `healthy`. Le contrôle de **03:30:05, heure de Paris**, a validé BBC et France 24 par URL seule avec relecture indépendante dans MongoDB Docker sur le port hôte 27018, le mode texte et deux entrées invalides. BBC a pris 29,235 secondes et France 24 4,423 secondes. L’API a ensuite été redémarrée ; `/ready` et les prédictions persistées ont été vérifiés de nouveau. Les rapports sont `verification_docker_optimise.json` et `optimisation_ressources.json`. Le changement de port hôte et l’installation sur un second ordinateur restent à vérifier.

MongoDB Docker a répondu et persisté les collectes initiales. La faible mémoire disponible a ensuite entraîné une erreur d’allocation lors de l’analyse avec Docker actif. Les documents du projet ont été sauvegardés puis importés dans une instance MongoDB Windows isolée sur `127.0.0.1:27019`. L’analyse et les rapports historiques utilisent cette base réelle. Le volume Docker conserve la collecte initiale. Le README présente le parcours Docker sur le port hôte `27018` pour les nouvelles installations.

Pendant cette nouvelle vérification, un chargement de l’API s’est interrompu avec le code natif Windows **3221225477 (`0xC0000005`, violation d’accès)**. Une relance avec le diagnostic Python `PYTHONFAULTHANDLER=1` activé a abouti et constitue le dernier rapport. La cause de l’arrêt natif reste à identifier. Le succès du dernier contrôle valide le parcours testé, tandis que la stabilité des démarrages répétés demande encore une investigation.

En mode hors ligne, Transformers 4.57.6 a également émis un avertissement de correction de regex Mistral pour ce tokenizer XLM-R. Le contrôle a conservé la configuration utilisée par le batch et a reproduit exactement son score. Cet avertissement de dépendance reste à examiner. La panne d’écriture MongoDB est couverte par les tests simulés existants. Le nouveau contrôle réel vérifie les écritures réussies et les validations d’entrée.

Les vérifications restantes concernent également une collecte plus large, le corps anglais de GameSpot refusé en HTTP 403, l’adaptation du point d’entrée France 3, une calibration sur corpus annoté et une reproduction Docker sur un second ordinateur. Les restrictions des sources et les anciennes instabilités natives Windows restent distinctes du parcours Docker désormais validé.

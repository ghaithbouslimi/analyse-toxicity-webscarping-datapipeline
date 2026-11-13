# Choix techniques

## Architecture et traçabilité

`cli.py` orchestre les commandes. `pipeline.py` découvre, collecte et analyse. `collecte` centralise HTTP et extraction. `prediction` est partagé avec FastAPI. `stockage` centralise les écritures et index. `statistiques.py` produit les résultats enregistrés et les exports.

Les collections `articles`, `run_articles`, `predictions`, `pipeline_runs` et `site_statistics` conservent respectivement le dernier article, les snapshots et exclusions par run, les scores et snapshots, les paramètres d’exécution et les statistiques. `run_articles` complète la structure proposée pour préserver les textes exclus et les versions utilisées. Les identifiants déterministes et upserts garantissent l’idempotence des articles et résultats batch. Un historique API utilise un UUID pour chaque demande réussie. Les index uniques protègent les clés concurrentes.

La prédiction batch est écrite avant son pointeur dans l’observation. En cas d’arrêt entre ces opérations, une reprise retrouve la même clé et finalise le pointeur. Les statistiques sélectionnent les pointeurs effectivement finalisés. Un ancien snapshot reste dans `predictions` lorsqu’un article courant évolue. La collecte d’un run est figée après initialisation de sa configuration de scoring.

La période est `[début, fin]` en UTC, avec une fin fixée lors de la création. Les dates de publication explicites JSON-LD et Open Graph précèdent celles du flux, puis l’heuristique Trafilatura. Une date sans fuseau est interprétée en UTC. Les dates inconnues sont exclues. Le hash SHA-256 porte sur le texte extrait en UTF-8. Les URL de suivi sont normalisées, les URL canoniques sont validées et dédupliquées avant d’incrémenter le plafond.

## Accès HTTP et extraction

HTTPX applique des timeouts et une limite globale de concurrence. Chaque hôte a un verrou et un délai entre requêtes. Les redirections sont contrôlées à chaque saut. Les domaines apex et `www` déclarés sont autorisés, avec le préfixe `/fr/` pour France 24. Les destinations réseau arbitraires, identifiants intégrés et ports inattendus sont rejetés. `robots.txt` est consulté avant les ressources. Un fichier inaccessible bloque la source de manière observable. Son absence HTTP 404 autorise la poursuite.

Les réponses transitoires HTTP 429 et 500/502/503/504 sont réessayées au maximum trois fois par défaut. `Retry-After` est respecté. Une temporisation supérieure à 60 secondes diffère le téléchargement en enregistrant une exclusion, ce qui évite une attente prolongée du batch. La taille décompressée est limitée à 8 Mo. Trafilatura extrait le corps en excluant les commentaires. Beautiful Soup lit les métadonnées et les liens de rubrique en secours du RSS.

Les points d’entrée des huit sources figurent dans `configuration/sources.yaml`. Leur disponibilité est réévaluée à chaque run. Les erreurs du flux et de la rubrique restent dans les observations. Le seuil de 300 caractères est un filtre de qualité initial. Un paywall déclaré par `isAccessibleForFree=false` entraîne une exclusion. L’extraction de pages payantes partiellement servies demeure une limite de détection, à contrôler manuellement sur chaque échantillon.

## Modèle et sorties

La révision officielle vérifiée est `4ad6f5c104d9ce813a1a2f33cac0c5b579ef6ee5` de `unitary/multilingual-toxic-xlm-roberta`. La licence déclarée est Apache-2.0. La fiche décrit un modèle multilingue pour les commentaires Jigsaw et inclut français et anglais. Elle signale des différences de résultats avec Detoxify. Cette implémentation utilise directement les poids Hugging Face versionnés. [Fiche du modèle](https://huggingface.co/unitary/multilingual-toxic-xlm-roberta/blob/4ad6f5c104d9ce813a1a2f33cac0c5b579ef6ee5/README.md)

La configuration expose `id2label={0: toxic}` et un unique logit. Le code vérifie ce contrat avant toute inférence puis applique une sigmoïde. La sortie n’utilise aucune hypothèse sur l’ordre de labels génériques. Les poids PyTorch de la révision sont chargés explicitement, avec `trust_remote_code=False` et PyTorch récent. [Configuration officielle](https://huggingface.co/unitary/multilingual-toxic-xlm-roberta/blob/4ad6f5c104d9ce813a1a2f33cac0c5b579ef6ee5/config.json)

La capacité effective XLM-R est calculée à partir du tokenizer, des embeddings de position et du padding. Les passages réservent les tokens spéciaux. Aucun passage n’est retiré silencieusement. Le batch initial est ramené à un passage et deux threads CPU, au vu des 8 Go de RAM et de la faible mémoire disponible lors de l’inspection. Le sémaphore d’inférence est réglé à un. Ces valeurs sont configurables.

`MODEL_DTYPE` permet `float32`, `float16` et `bfloat16`. La valeur par défaut est désormais `float16`, déjà utilisée pour les rapports livrés après un échec d’allocation de 768 Mo en float32. La précision numérique figure dans la configuration et dans son hash. Une comparaison entre exécutions doit conserver ce paramètre. Un seul thread de calcul est utilisé par défaut ; le parallélisme interop PyTorch est limité à un thread et celui du tokenizer est désactivé. L’image limite également les threads OpenBLAS, OpenMP, MKL et Rayon. Compose applique en complément des plafonds CPU et mémoire aux conteneurs. Ces limites bornent la consommation sans garantir une latence plus courte.

Le maximum des passages augmente le risque de faux positifs avec la longueur. Les citations d’insultes, le discours rapporté et les identités mentionnées peuvent être mal classés. Les catégories du sujet sont opérationnalisées par deux bandes de scores provisoires. Une validation de gravité et une calibration nécessitent un corpus annoté de presse française et anglaise. Un score élevé décrit la sortie du classifieur. La documentation du modèle précise les biais liés à la présence de termes offensants. [Limites du modèle](https://huggingface.co/unitary/multilingual-toxic-xlm-roberta)

Le contrôle réel en float16 du 12 novembre 2026 a classé les deux phrases neutres française et anglaise sous 0,001, et les deux insultes au-dessus de 0,995. La citation judiciaire a reçu 0,7964 et illustre un faux positif contextuel selon la lecture manuelle proposée. Le texte neutre répété de 2 400 tokens a été traité en cinq passages, avec un maximum de 0,001642. L’échantillon ne suffit pas à estimer les taux de faux positifs ou de faux négatifs.

Sur ce contrôle, le chargement en cache a pris 7,706 secondes après les imports Python. Les phrases courtes ont pris entre 0,308 et 0,414 seconde et le texte long 39,594 secondes. Le RSS échantillonné après les phrases courtes a atteint environ 560 Mo. Ces valeurs décrivent une mesure sur cette machine occupée et le RSS instantané échantillonné. Le JSON brut est conservé dans `rapports/verification_modele.json`.

## API et statistiques

L’API charge le modèle au démarrage et conserve un client MongoDB et un téléchargeur HTTP par processus. `POST /predict` est asynchrone pour le téléchargement ; l’extraction, l’inférence et les écritures synchrones utilisent `asyncio.to_thread`. Le sémaphore borne les calculs CPU. La réponse 200 suit l’écriture acquittée de la prédiction en base. [Concurrence FastAPI](https://fastapi.tiangolo.com/async/)

Avec `text`, `source_url` reste une métadonnée. Avec uniquement `source_url`, l’API réutilise le téléchargement et l’extraction du collecteur et analyse le texte obtenu avec le même service de prédiction. L’article courant est enregistré dans `articles` et la prédiction conserve un snapshot du texte, son hash et les métadonnées d’extraction. Si l’écriture de la prédiction échoue après celle de l’article, l’article peut rester enregistré mais aucune réponse 200 n’est produite. Ces documents API sont exclus des agrégations batch.

Le mode URL accepte les domaines Internet publics en dehors des huit sources batch. Chaque destination, y compris `robots.txt` et chaque redirection, est contrôlée. La résolution DNS est limitée dans le temps ; toutes les adresses doivent être publiques et la connexion utilise directement une adresse validée. Le nom HTTP et le nom TLS restent ceux du domaine demandé. Les connexions ne sont pas réutilisées entre requêtes afin d’éviter de partager une session TLS entre des domaines ayant la même IP. Le transport ignore les proxys d’environnement. Le batch conserve son contrôle de domaine configuré. [Extension SNI HTTPcore](https://www.encode.io/httpcore/extensions/#sni-hostname)

Le mode URL refuse les pages payantes, les réponses non HTML et les extractions incomplètes. Il n’impose ni la fenêtre de collecte ni une date publiée connue ; `unknown_date` reste visible dans la réponse. Les règles de taille, robots et temporisation restent appliquées. Aucun navigateur JavaScript ni accès authentifié n’est ajouté.

Le dénominateur par site est le nombre de snapshots batch scorés et référencés dans le run avec sa configuration. Le rapport conserve également les comptes de collecte, les exclusions et le taux de couverture. Les pourcentages nuls et l’absence de données sont distingués. Les prédictions API et historiques batch détachés du run sont filtrés. La liste des sources est figée dans le run pour conserver les sites sans données. Le classement décrit exclusivement l’échantillon observé.

Les index uniques et `$setOnInsert` rendent les écritures batch atomiques par document. Les statistiques sont remplacées par site et run. [Index uniques MongoDB](https://www.mongodb.com/docs/manual/core/index-unique/)

## Dépendances et reproductibilité

Python 3.11 est imposé dans `pyproject.toml`. `uv 0.13.7` a résolu et installé les dépendances. Les versions effectives figurent dans `uv.lock`. L’export `requirements.lock` contient les hashes. Transformers est limité à la branche 4.57, avec PyTorch CPU compatible et `protobuf` requis par la conversion du tokenizer XLM-R. L’image MongoDB 8.0 est figée par digest. Le cache modèle et les volumes sont persistants. [Installation Transformers](https://huggingface.co/docs/transformers/installation), [API Trafilatura](https://trafilatura.readthedocs.io/en/latest/corefunctions.html)

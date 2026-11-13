# Ressources, journaux et format de livraison

## Diagnostic du 13 novembre 2026

Le fichier joint contenait 14 événements MongoDB de sévérité `I` : métadonnées de clients, ouvertures et fermetures de connexions, premières commandes et connexions sans authentification. Le client annoncé était `mongosh`, utilisé par le contrôle de santé du service. Ces lignes ne constituent pas une erreur d’API ni une preuve de manque de mémoire.

L’ancien conteneur API lancé isolément échouait avec `model_revision: Field required`. L’image définit désormais la révision figée, et le lancement documenté utilise Compose pour fournir le réseau, MongoDB, les variables et les volumes.

C: ne disposait que d’environ 212 Mo libres. Le disque virtuel Docker, d’environ 7,4 Go, se trouvait sous le profil Windows sur C:. Avec accord de l’utilisateur, Docker Desktop l’a déplacé vers `D:/CodexDataEngineerCache/docker-desktop/DockerDesktopWSL`. Les images et volumes existants ont été conservés. L’espace libre mesuré après le déplacement était d’environ 7,5 Go. Les nouvelles images et les volumes nommés utilisent désormais ce stockage sur D:.

Le cache du modèle et l’environnement Python applicatif étaient déjà sur D:. Le cache local contient deux formats de poids d’environ 1,11 Go chacun ; l’application utilise le format PyTorch avec `use_safetensors=False`. Une nouvelle installation par la commande fournie n’a besoin que de ce format. Les deux formats existants ont été conservés.

## Optimisations appliquées

| Composant | Valeur par défaut | Portée |
| --- | --- | --- |
| API Docker | 1 cœur CPU, 2 Gio maximum | Limite du conteneur en fonctionnement |
| MongoDB Docker | 0,5 cœur CPU, 512 Mio maximum | Limite du conteneur en fonctionnement |
| Cache WiredTiger | 0,25 Gio | Cache interne, distinct de la mémoire totale MongoDB |
| Inférence | float16, un thread, un calcul à la fois | Même modèle et mêmes seuils |
| Tokenizer et bibliothèques CPU | Parallélisme limité | OpenBLAS, OpenMP, MKL, Rayon et interop PyTorch |
| Demandes API | Deux demandes au maximum | HTTP 429 et Retry-After au-delà |
| Journaux | Deux fichiers de 5 Mo par service | Rotation gérée par Docker |
| Contrôles de santé | MongoDB 30 s, API 60 s | Moins de lancements de mongosh et Python |
| Installation des bibliothèques | Deux téléchargements et une installation simultanés | Réduit le parallélisme de construction |

Un cœur CPU correspond à l’équivalent d’un cœur, pas à un pourcentage fixe du processeur complet. Dans `docker stats`, 100 % correspond généralement à un cœur utilisé. Le moteur Docker, WSL et les autres applications consomment également des ressources. Les plafonds des services ne plafonnent pas la construction des images. Réduire `API_CPUS` allonge potentiellement les analyses.

L’analyse réelle Docker de BBC a traité 5 068 caractères en environ 29,2 secondes et celle de France 24, 535 caractères en environ 4,4 secondes. Les deux sites et les deux appels API ont renvoyé HTTP 200, avec lecture indépendante des prédictions dans MongoDB. Les rapports détaillés sont `rapports/verification_docker_optimise.json` et `rapports/optimisation_ressources.json`.

Le score BBC float16 dans Linux est 0,1330566, contre 0,1331787 lors du contrôle Windows précédent. Cette petite variation numérique ne change pas la catégorie non toxique ; l’identité bit à bit entre plateformes n’est pas garantie.

## Restrictions des sources

| Source | Limite observée dans la collecte de référence |
| --- | --- |
| GameSpot, Marianne | Refus HTTP 403 sur les articles ou points d’entrée |
| Le Monde | Page de protection et extraction incomplète |
| Mediacités | Contenu signalé payant |
| Le Point | robots.txt inaccessible en HTTP 403 |
| France 3 régions | Flux HTTP 404 et découverte de secours insuffisante |

Ces observations sont distinctes des incidents disque et mémoire qui ont affecté l’installation et le chargement. Déplacer Docker vers D: ne lève pas les restrictions d’accès des éditeurs. L’API conserve aussi des limites explicites : 8 Mo décompressés pour une réponse HTTP et 20 000 caractères de texte par défaut. Un dépassement est signalé ; le texte n’est pas tronqué silencieusement.

## Livraison inférieure à 20 Mo

La remise comprend le code, les tests, la configuration, les verrous, la documentation et les rapports. Les bibliothèques, images Docker, données MongoDB et poids sont externes à l’archive. Le poids nécessaire au modèle seul dépasse 1,1 Go ; float16 à l’exécution ne réduit pas le fichier téléchargé. Une archive autonome hors ligne avec tous ces composants ne tient donc pas dans 20 Mo.

Le premier démarrage télécharge les dépendances et le modèle. Les volumes conservent ensuite le modèle et les données. Le guide de remise décrit cette installation ; aucun chemin D: propre à la machine de réalisation n’est imposé au recruteur.

```powershell
.venv311\Scripts\python.exe scripts/preparer_livraison.py
```

Le script crée `livraison/Ghaith_Bouslimi_Data_Engineer.zip`, vérifie une taille strictement inférieure à 20 000 000 octets et contrôle l’intégrité ZIP. Le guide figure à la racine de l’archive et un manifeste contient les hashes des fichiers du projet. Les environnements, secrets `.env`, caches, journaux et données locales sont exclus.

Le serveur Docker utilise MongoDB sur le port hôte 27018. L’ancienne instance Windows sur 27019 est conservée avec son historique et constitue une base distincte. Pour consulter les nouvelles prédictions Docker dans Compass : `mongodb://127.0.0.1:27018/analyse_toxicite`, sans authentification pour cette démonstration locale.

Références : [ressources Compose](https://docs.docker.com/reference/compose-file/services/), [rotation des journaux](https://docs.docker.com/engine/logging/drivers/json-file/), [réglages Docker Desktop](https://docs.docker.com/desktop/settings-and-maintenance/settings/), [options MongoDB](https://www.mongodb.com/docs/manual/reference/program/mongod/).

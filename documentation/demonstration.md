# Démonstration en cinq minutes

Préparer l’environnement et le cache avant l’entretien. Choisir le run complet dans `documentation/validation.md` ou créer un nouveau run. Les téléchargements et collectes variables selon les sources se préparent en amont.

## Minute 1

Présenter les modules de `src/analyse_toxicite`. Expliquer le parcours découverte → extraction → MongoDB → prédiction partagée → statistiques. Ouvrir le fichier de sources et la période du run avec `toxicite etat --run-id <identifiant>`.

## Minute 2

Ouvrir le rapport CSV et le graphique du run. Montrer les sources, les effectifs et les exclusions. Expliquer que les sites sans articles scorés affichent « données insuffisantes ». Pour un run créé dans MongoDB Docker, comparer les nombres à `site_statistics` et `run_articles` dans Compass avec `mongodb://127.0.0.1:27018/analyse_toxicite`. Les rapports historiques livrés conservent le contexte de leur exécution dans la matrice de validation.

## Minute 3

Ouvrir `/docs`. Envoyer une phrase française puis une phrase anglaise à `/predict`. Montrer le score de toxicité, la confiance de décision, la révision et les scores de passages. Vérifier les documents `origin=api` dans MongoDB. Envoyer un texte composé d’espaces et constater HTTP 422.

Choisir ensuite l’exemple **Article par URL**. Envoyer uniquement `source_url` avec l’URL d’un article public. La réponse inclut `article.title`, `article.http_status` et `article.text_characters`. Retrouver la prédiction grâce à `prediction_id` et montrer que `text` contient le corps extrait de l’article. Une erreur du site, une restriction robots ou une extraction incomplète doit être expliquée à partir du message reçu ; elle ne produit pas de prédiction réussie.

## Minute 4

Présenter `prediction/service.py` et `decoupage.py`. Expliquer l’unique logit, la sigmoïde, la réserve des tokens spéciaux, le maximum des passages et les limites des bandes 0,5/0,8. Montrer les mesures CPU de `verifier-modele` si disponibles. Expliquer les erreurs d’accès observées sur les sources.

## Minute 5

Exécuter `pytest -q` et `ruff check src tests`. Relancer `toxicite analyser --run-id <identifiant>` et `toxicite rapport --run-id <identifiant>`. Vérifier que les effectifs restent identiques. Montrer le port configurable et les volumes dans Compose, puis conclure sur les vérifications réellement réalisées dans la matrice.

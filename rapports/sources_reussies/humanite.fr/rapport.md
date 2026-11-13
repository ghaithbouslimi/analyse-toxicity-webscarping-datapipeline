# Rapport de L’Humanité

Source suivie sous le domaine `humanite.fr`. Le rapport porte sur 3 articles téléchargés avec HTTP 200 OK, extraits et analysés avec succès.

Les statuts HTTP sont ceux enregistrés lors de la collecte du run. Chaque résultat présenté correspond au même snapshot de texte dans `run_articles` et dans une prédiction batch de MongoDB.

Run `4d717f8d-b1c7-4c5f-8cdb-93bcc13e374c`.

Période de publication du 29/10/2026 à 16:53:27 UTC au 12/11/2026 à 16:53:27 UTC.

| Résultat sur les articles retenus | Effectif | Part |
| --- | --- | --- |
| Téléchargement HTTP 200, extraction et analyse réussis | 3 | 100 % |
| Non toxique | 3 | 100 % |
| Légèrement toxique | 0 | 0 % |
| Très toxique | 0 | 0 % |

Le dénominateur des pourcentages est de 3 articles effectivement analysés.

Les articles retenus et leurs résultats sont détaillés ci-dessous.

**Attentat raciste de Trappes : une liste de personnalités de gauche retrouvée au domicile de Kevin T (Video) - L'Humanité**

- Publication le 12/11/2026 à 16:45:00 UTC.
- Téléchargement le 12/11/2026 à 16:53:34 UTC, réponse **HTTP 200 OK**.
- Extraction réussie, **1138 caractères** dans le snapshot analysé.
- Analyse enregistrée le 12/11/2026 à 18:47:08 UTC, 293 tokens et 1 passage(s).
- Prédiction **Non toxique**, catégorie non toxique.
- Score de toxicité **0,070556641** et confiance de décision **0,929443359**.
- Scores des passages 0,070556641.
- Identifiant de prédiction `737079bcea2d46e5181bd86cf3695bdefc6722aa5e8158c8e1989d026b422244`.
- Empreinte SHA-256 du texte `e979c6b89edb8b5936ba7ceebdf14e68eabf190b59d489331f971d97cfb6f045`.

[Page source téléchargée](https://www.humanite.fr/politique/attentat-raciste-de-trappes/attentat-raciste-de-trappes-une-liste-de-personnalites-de-gauche-retrouvee-au-domicile-de-kevin-t)

**Au-delà d’un pouvoir d’achat, les Français veulent un pouvoir de vivre - L'éditorial de Maud Vergnol - 12 novembre 2026 | L'Humanité : lire, agir**

- Publication le 12/11/2026 à 16:10:39 UTC.
- Téléchargement le 12/11/2026 à 16:53:36 UTC, réponse **HTTP 200 OK**.
- Extraction réussie, **2944 caractères** dans le snapshot analysé.
- Analyse enregistrée le 12/11/2026 à 18:47:17 UTC, 742 tokens et 2 passage(s).
- Prédiction **Non toxique**, catégorie non toxique.
- Score de toxicité **0,003171921** et confiance de décision **0,996828079**.
- Scores des passages 0,000718117, 0,003171921.
- Identifiant de prédiction `b290bd4d78a07bab5605a854ef40c8bd0cd6854cf106ffd1ab02d107cd7f1f6d`.
- Empreinte SHA-256 du texte `3712005938f8bc8520712efc79cd108e5d308c8d232fef4f0f60c8a227b624b5`.

[Page source téléchargée](https://www.humanite.fr/en-debat/marche-contre-la-vie-chere/sau-dela-dun-pouvoir-dachat-les-francais-veulent-un-pouvoir-de-vivre)

**Agriculture : le gouvernement annonce un plan de relance à 725 millions d’euros pour l’adaptation au changement climatique - L'Humanité**

- Publication le 12/11/2026 à 15:50:49 UTC.
- Téléchargement le 12/11/2026 à 16:53:38 UTC, réponse **HTTP 200 OK**.
- Extraction réussie, **2676 caractères** dans le snapshot analysé.
- Analyse enregistrée le 12/11/2026 à 18:47:27 UTC, 667 tokens et 2 passage(s).
- Prédiction **Non toxique**, catégorie non toxique.
- Score de toxicité **0,030792236** et confiance de décision **0,969207764**.
- Scores des passages 0,000414133, 0,030792236.
- Identifiant de prédiction `193609d3b7ecc1262034ae16873c5c2fa365dd3fad3f714361b591bce6ccdc03`.
- Empreinte SHA-256 du texte `3faacec70bca3d99ce1a356b3ce9a051d8bd232b14bd0c5586e8273b2879ddc8`.

[Page source téléchargée](https://www.humanite.fr/environnement/agriculture/agriculture-le-gouvernement-annonce-un-plan-de-relance-a-725-millions-deuros-pour-ladaptation-au-changement-climatique)

Les trois textes de cet échantillon ont un score inférieur au seuil de 0,5. Les scores sont non calibrés et les bandes 0,5–0,8 et 0,8–1 sont provisoires. L’effectif de trois articles limite la généralisation à l’ensemble du site.

Modèle `unitary/multilingual-toxic-xlm-roberta`, révision `4ad6f5c104d9ce813a1a2f33cac0c5b579ef6ee5`, exécuté sur cpu en float16. Le score de toxicité provient d’une sigmoïde. L’agrégation `max-v1` retient le maximum des passages.

Configuration de scoring `a3a617c86e38e5e056efb23993a8affcf8bb2f096d87fb41eb87137af9e09871`.

Rapport généré le 12/11/2026 à 22:12:49 UTC à partir des données enregistrées dans MongoDB.

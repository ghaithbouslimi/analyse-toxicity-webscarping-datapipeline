# Rapport de France 24

Source suivie sous le domaine `france24.com`. Le rapport porte sur 3 articles téléchargés avec HTTP 200 OK, extraits et analysés avec succès.

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

**Élément Terre, la quotidienne - COP31: L'Union Européenne se désengage-t-elle de la diplomatie climatique?**

- Publication le 12/11/2026 à 16:48:33 UTC.
- Téléchargement le 12/11/2026 à 16:53:34 UTC, réponse **HTTP 200 OK**.
- Extraction réussie, **855 caractères** dans le snapshot analysé.
- Analyse enregistrée le 12/11/2026 à 18:46:40 UTC, 219 tokens et 1 passage(s).
- Prédiction **Non toxique**, catégorie non toxique.
- Score de toxicité **0,000407696** et confiance de décision **0,999592304**.
- Scores des passages 0,000407696.
- Identifiant de prédiction `1bf6fb2e194d65201101e635597e36f14e47ae25f405d7437daecc67bc22cd18`.
- Empreinte SHA-256 du texte `4b0ca7aee0ba3681af687fec391b1942bdda13342caacf31083a9ba988434795`.

[Page source téléchargée](https://www.france24.com/fr/%C3%A9missions/%C3%A9l%C3%A9ment-terre-la-quotidienne/20261112-cop31-l-union-europ%C3%A9enne-se-d%C3%A9sengage-t-elle-de-la-diplomatie-climatique)

**Ces images relayées par Israël prouvent-elles vraiment que la nourriture est abondante à Gaza ?**

- Publication le 12/11/2026 à 16:42:29 UTC.
- Téléchargement le 12/11/2026 à 16:53:36 UTC, réponse **HTTP 200 OK**.
- Extraction réussie, **6823 caractères** dans le snapshot analysé.
- Analyse enregistrée le 12/11/2026 à 18:47:01 UTC, 1615 tokens et 4 passage(s).
- Prédiction **Non toxique**, catégorie non toxique.
- Score de toxicité **0,001394272** et confiance de décision **0,998605728**.
- Scores des passages 0,000474691, 0,000412464, 0,000452995, 0,001394272.
- Identifiant de prédiction `5777cc16b5dc174a7be0e617b4e1232755ab49f0767946d112bd1ab09b82bc60`.
- Empreinte SHA-256 du texte `fd7f4d60f2aa8f624fb92ab4355a8125e4797ea5b430e554261c1aa320931c96`.

[Page source téléchargée](https://www.france24.com/fr/moyen-orient/20261112-ces-images-relay%C3%A9es-par-isra%C3%ABl-prouvent-elles-vraiment-que-la-nourriture-est-abondante-%C3%A0-gaza)

**États-Unis : Donald Trump retire le dossier de la guerre en Iran à JD Vance**

- Publication le 12/11/2026 à 16:38:21 UTC.
- Téléchargement le 12/11/2026 à 16:53:38 UTC, réponse **HTTP 200 OK**.
- Extraction réussie, **800 caractères** dans le snapshot analysé.
- Analyse enregistrée le 12/11/2026 à 18:47:04 UTC, 198 tokens et 1 passage(s).
- Prédiction **Non toxique**, catégorie non toxique.
- Score de toxicité **0,001028061** et confiance de décision **0,998971939**.
- Scores des passages 0,001028061.
- Identifiant de prédiction `b06ae744b80d7ea676df68e0cc86aa29b5c30188721a59ce8f36f53559c5d168`.
- Empreinte SHA-256 du texte `0531102b43c4aad28de9b6a482945e170c3b5960391fe7370c20f5c7dd9f524b`.

[Page source téléchargée](https://www.france24.com/fr/vid%C3%A9o/20261112-%C3%A9tats-unis-donald-trump-retire-le-dossier-de-la-guerre-en-iran-%C3%A0-jd-vance)

Les trois textes de cet échantillon ont un score inférieur au seuil de 0,5. Les scores sont non calibrés et les bandes 0,5–0,8 et 0,8–1 sont provisoires. L’effectif de trois articles limite la généralisation à l’ensemble du site.

Modèle `unitary/multilingual-toxic-xlm-roberta`, révision `4ad6f5c104d9ce813a1a2f33cac0c5b579ef6ee5`, exécuté sur cpu en float16. Le score de toxicité provient d’une sigmoïde. L’agrégation `max-v1` retient le maximum des passages.

Configuration de scoring `a3a617c86e38e5e056efb23993a8affcf8bb2f096d87fb41eb87137af9e09871`.

Rapport généré le 12/11/2026 à 22:12:49 UTC à partir des données enregistrées dans MongoDB.

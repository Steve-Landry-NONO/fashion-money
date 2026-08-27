# Fashion Money — Rapport d’avancement & feuille de route

> **Date :** 27 août 2026  
> **Branche de référence :** `feat/vision-smoke-test-harness`  
> **PR active :** #8 — `test: validate collage-aware vision decomposition`  
> **But de ce document :** donner une vue unique de ce qui est déjà livré/visible dans le repository, de ce qui est encore en cours, de la suite du plan produit/technique, des documents à remettre à jour et des nouvelles idées à intégrer sans perdre le wedge initial.

---

## 1. Positionnement produit à préserver

Fashion Money n’est pas une app de shopping à laquelle on ajoute de l’IA. Le produit est une **couche de décision** qui relie :

1. **le budget vestimentaire** de l’utilisateur ;
2. **sa garde-robe réelle** ;
3. **ses inspirations** (captures, photos, partage depuis des apps sociales) ;
4. **les produits achetables** permettant de compléter un look.

Le positionnement reste :

- **budget-first = moat** ;
- **capture-first = déclencheur d’usage** ;
- **vision + recherche produit = commodités intégrées** ;
- **wallet + matching + decision = cœur différenciant**.

La boucle cible reste :

```text
Capture / inspiration
        ↓
Vision / décomposition du look
        ↓
Sélection de l’outfit si plusieurs looks
        ↓
Matching avec la garde-robe
        ↓
Gaps : ce qu’il manque réellement
        ↓
Product Search réel
        ↓
Options achetables classées
        ↓
Impact sur le budget AVANT achat
        ↓
Décision : acheter / attendre / substituer / étaler / recréer
        ↓
Confirmation d’achat
        ↓
Wallet + garde-robe mis à jour
        ↓
Valeur cumulative à la capture suivante
```

---

# 2. Ce qui est déjà visible dans le repository

## 2.1 Fondation backend — PR #1 ✅ mergée

Le repository contient désormais un vrai socle backend :

- FastAPI ;
- PostgreSQL ;
- Alembic ;
- Docker Compose ;
- MinIO prévu comme object storage S3-compatible ;
- CI GitHub ;
- identité de développement ;
- structure modulaire par domaines : Wallet, Decision, Matching, Capture, Catalog, Analytics.

La première PR a également introduit les documents structurants :

- `docs/PRD-v1.md` ;
- `docs/technical-design-v1.md` ;
- `docs/vertical-slice-1.md` ;
- `docs/decisions-applied.md`.

### État

**Livré et mergé dans `main`.**

---

## 2.2 Wallet Engine + ledger append-only ✅

Le budget n’est pas stocké comme un simple champ `remaining` mutable.

Le système utilise un **ledger append-only** avec les mouvements :

- `SPEND` ;
- `ADJUST` ;
- `ROLLOVER_IN`.

Le solde est dérivé :

```text
available = base + Σ ROLLOVER_IN − Σ SPEND + Σ ADJUST
```

Cela nous donne :

- auditabilité ;
- historique ;
- calcul reproductible ;
- report mensuel déterministe ;
- meilleure sécurité pour les futures fonctions de recommandation financière.

### État

**Implémenté, testé et mergé.**

---

## 2.3 Walking skeleton du moat — PR #2 ✅ mergée

Le premier parcours backend de bout en bout existe avec providers mockés :

```text
budget
→ capture mock
→ decomposition mock
→ matching garde-robe
→ gap
→ options produits mock
→ decision
→ confirmation achat
→ wallet + garde-robe
→ analytics
```

Éléments déjà implémentés :

- `DecompositionProvider` interchangeable ;
- `ProductSearchProvider` interchangeable ;
- matching attribut-based ;
- calcul des gaps ;
- options produits mockées ;
- Decision Engine `fits | tight | over` ;
- décision sans effet de bord ;
- confirmation d’achat atomique ;
- idempotence de confirmation ;
- ajout simultané dans la garde-robe ;
- débit simultané du Wallet.

### État

**Implémenté, testé et mergé.**

---

## 2.4 Vague B — budget avancé et régimes de décision — PR #3 ✅ mergée

Le système comprend maintenant :

- report mensuel ;
- plafond de rollover ;
- sécurité de replay/idempotence ;
- états `fits`, `tight`, `over` ;
- stubs d’interface pour :
  - **phasing** / étalement ;
  - **substitution** / version qui rentre dans le budget ;
- exposition à parité des deux stratégies dans l’état `over`.

Important : les algorithmes intelligents de phasing/substitution ne sont **pas encore** implémentés ; seule leur interface produit/technique est figée.

### État

**Implémenté, testé et mergé.**

---

## 2.5 Analytics H3 / compounding — PR #4 ✅ mergée

L’instrumentation permet maintenant de mesurer la transition :

```text
J0
→ premier achat
→ garde-robe enrichie
→ capture suivante
→ owned_pct potentiellement supérieur
→ meilleure décision
```

Le repository contient notamment :

- `capture_index` ;
- taille de garde-robe ;
- régime `j0` / `mature` ;
- `owned_pct` ;
- `decision_action_taken` ;
- `return_session` ;
- nombre de pièces avant/après achat.

L’activation reste volontairement définie comme une **action de décision**, pas comme la simple consultation d’un écran.

### État

**Implémenté, testé et mergé.**

---

## 2.6 Premier client mobile Expo / React Native — PR #5 ✅ mergée

Le repository contient une vraie app mobile Expo/RN reliée au backend.

La boucle visible couvre :

- configuration du budget ;
- wallet ;
- capture mockée ;
- matching / gap ;
- options ;
- décision ;
- confirmation d’achat ;
- retour à une capture suivante pour matérialiser le compounding.

Les règles financières restent côté serveur : le mobile consomme l’état retourné par l’API.

### État

**Implémenté et mergé.**

---

## 2.7 Import réel depuis la galerie — PR #6 ✅ mergée

Le mobile permet désormais :

- d’ouvrir la galerie ;
- de sélectionner une capture ou une image réelle ;
- de la prévisualiser ;
- de lancer l’analyse depuis cette entrée réelle.

À cette étape, l’image n’était encore qu’une URI locale transmise au backend : le provider Vision restait mocké.

### État

**Implémenté et mergé.**

---

## 2.8 Upload réel + object storage + Vision — PR #7 ✅ mergée

Le saut technologique majeur précédent est déjà dans `main` :

- endpoint multipart réel ;
- upload JPEG / PNG / WEBP ;
- stockage objet S3-compatible ;
- MinIO local ;
- validation de taille/type média ;
- bytes de l’image réellement envoyés au provider Vision ;
- provider Vision interchangeable ;
- mobile envoyant désormais les vrais bytes de l’image.

Le Product Search reste volontairement mocké.

### État

**Implémenté et mergé.**

---

# 3. Travail Vision actuel — PR #8 🟡 en cours

La PR #8 est notre phase de validation réelle de la qualité Vision.

## 3.1 Smoke test réel

Nous avons construit un harness local capable de prendre **3 à 5 captures réelles** et de produire un rapport JSON mesurable.

Le jeu de référence actuel contient quatre collages de looks :

- `01_bleu_creme.jpeg` ;
- `02_noir_beige.jpeg` ;
- `03_beige_bleu.jpeg` ;
- `04_creme_marron.jpeg`.

Les images et les rapports restent locaux et ne sont pas commités.

---

## 3.2 Ce que V1 nous a appris

Le premier contrat était :

```text
style
pieces[]
```

Sur des collages multi-personnes, le modèle fusionnait plusieurs looks en une pseudo-tenue de **10–11 pièces**.

Conclusion : ce contrat était insuffisant.

---

## 3.3 Nouveau contrat collage-aware

Le contrat Vision est désormais :

```text
image_type
style
dominant_palette[]
outfits[]
    style
    pieces[]
        category_raw
        category
        color
        cut
        material
        swatch
        confidence
representative_outfit_index
```

Bénéfices :

- séparation des différentes personnes / looks ;
- conservation de la catégorie brute ;
- catégorie normalisée ;
- attributs facultatifs ;
- incertitude mesurable ;
- compatibilité temporaire avec l’ancien pipeline via l’outfit représentatif.

---

## 3.4 Normalisation de catégories

Première couche déterministe déjà présente :

```text
pants / slacks        → trousers
polo shirt            → polo
tee / t shirt         → t-shirt
loafer / loafers      → shoes
penny/tassel loafer   → shoes
sneaker               → sneakers
```

Objectif : éviter qu’un même type de vêtement soit considéré comme plusieurs catégories par le Matching Engine ou le futur Product Search.

---

## 3.5 Passage OpenAI → Groq

Le développement ne dépend plus d’une clé OpenAI.

Le provider Groq a été ajouté derrière la même abstraction de décomposition.

Configuration locale :

```text
DECOMPOSITION_PROVIDER=groq
GROQ_API_KEY=<secret local>
VISION_MODEL=...
```

Le secret reste dans `backend/.env`, ignoré par Git.

---

## 3.6 Comparatif réel Qwen 3.6 vs Qwen 3.8

### Qwen 3.6

Nous avons observé :

- qualité de détection intéressante ;
- segmentation parfois correcte ;
- erreurs récurrentes `json_validate_failed` ;
- fiabilité structurée insuffisante pour production.

Différents durcissements de prompt ont été testés. Ils ont parfois amélioré la segmentation mais pas la stabilité globale de la sortie JSON.

### Qwen 3.8

Le smoke test V2.3 sur **exactement les mêmes quatre captures** a donné :

```text
images_attempted  = 4
images_succeeded  = 4
images_failed     = 0
success_ratio     = 1.0
collages_detected = 4
avg_outfit_count  = 4.5
avg_pieces/outfit = 2.78
min               = 1
max               = 5
```

Autre signal important :

```text
missing_material_ratio = 0.76
```

Le modèle est donc beaucoup plus disposé à laisser `material = null` lorsqu’il n’a pas assez d’information visuelle, ce qui est préférable à l’hallucination.

### Défaut encore connu

Certains collages produisent un **ghost outfit** à une seule pièce. Exemple : une silhouette/zone peut être interprétée comme un look distinct.

Nous ne voulons pas sur-optimiser le provider pour ce cas avant le prochain jalon.

Réponse produit envisagée :

> lorsque plusieurs looks sont détectés, l’utilisateur choisit visuellement **« Quel look veux-tu recréer ? »**.

Cette interaction transforme une ambiguïté Vision en une sélection explicite et contrôlable.

### État

**Techniquement validé sur le smoke set avec Qwen 3.8. PR #8 encore à merger.**

---

# 4. État synthétique des PR

| PR | Sujet | État |
|---|---|---|
| #1 | Fondation FastAPI/Postgres/Wallet/docs | ✅ mergée |
| #2 | Moat E2E avec providers mockés | ✅ mergée |
| #3 | Rollover + régimes Decision + phasing/substitution stubs | ✅ mergée |
| #4 | Analytics J0/mature + compounding | ✅ mergée |
| #5 | Expo mobile vertical slice | ✅ mergée |
| #6 | Import réel depuis la galerie | ✅ mergée |
| #7 | Upload objet + Vision réelle | ✅ mergée |
| #8 | Smoke test Vision + Groq + collage-aware + Qwen 3.8 | 🟡 prête à finaliser/merger |

---

# 5. Où nous en sommes dans le plan global

Nous avons dépassé le **Vertical Slice 1 mocké** initial.

Le moat backend est déjà exécutable et la capture réelle existe. La Vision réelle a maintenant un provider suffisamment fiable pour continuer.

Le prochain mur n’est donc plus :

> « est-ce qu’une vraie image peut changer le résultat ? »

Cette étape est franchie.

Le prochain mur est :

> **« peut-on transformer une pièce manquante détectée en quelques vrais produits actuellement achetables, pertinents, comparables et compatibles avec le budget ? »**

---

# 6. Prochaine grande étape — Product Search réel

## Objectif

Remplacer `ProductSearchProvider` mocké sans modifier les appelants métier.

Entrée :

```text
normalized piece
+ color
+ cut
+ style context
+ budget available
```

Sortie minimale :

```text
product_id
merchant
name
category
price
currency
image_url
product_url
availability / stock if known
attributes
provider_score
```

## Travail à faire

- benchmarker les sources réellement accessibles ;
- choisir une stratégie initiale : API shopping/search/affiliate plutôt que scraping fragile ;
- concevoir un provider interchangeable ;
- sélectionner 3–5 produits utiles plutôt que 48 résultats ;
- intégrer prix réels ;
- gérer devises et pays ;
- conserver les URLs marchands ;
- définir expiration/fraîcheur d’une option ;
- filtrer/ordonner par budget ;
- mesurer clic marchand ;
- ne pas implémenter de checkout universel en V1.

## Gate attendu

Pour une pièce manquante :

```text
Vision
→ catégorie normalisée
→ requête produit
→ 3 produits pertinents
→ prix réel
→ Decision Engine
→ solde après achat
```

C’est le prochain jalon où Fashion Money commencera réellement à rapprocher **inspiration + commerce + budget**.

---

# 7. Sélection de l’outfit dans les collages

À construire en parallèle ou juste après Product Search.

## Problème

Vision sait maintenant renvoyer plusieurs `outfits[]`, mais l’interface mobile continue historiquement à consommer l’outfit représentatif.

## Évolution

Après analyse d’un collage :

```text
4 looks détectés

[look 1] [look 2]
[look 3] [look 4]

Quel look veux-tu recréer ?
```

Puis le pipeline métier travaille uniquement sur l’outfit choisi.

## À prévoir dans le domaine

- `selected_outfit_index` ;
- événement `outfit_selected` ;
- possibilité de changer de sélection ;
- relation entre capture et plusieurs looks ;
- réutilisation éventuelle de chaque outfit d’un même collage comme inspiration distincte.

---

# 8. Matching Engine — prochaine génération

Le matching actuel est attribut-based et volontairement débogable.

## À conserver

Ordre de poids recommandé pour le prochain stade :

```text
category    → très fort
color       → fort
cut         → moyen
material    → faible
```

`material` ne doit pas être un gate dur.

## Après collecte de données bêta

Possibilités :

- embeddings multimodaux ;
- similarité image ↔ garde-robe ;
- image ↔ produit ;
- apprentissage de préférences personnelles ;
- combinaison règles + embeddings ;
- explication utilisateur du match.

Le passage aux embeddings ne doit avoir lieu qu’après établissement d’un dataset de cas réels et de faux positifs/faux négatifs.

---

# 9. Garde-robe numérique — réduire le cold start

La garde-robe reste centrale au compounding H3.

## Déjà possible / prévu

- ajout après achat confirmé ;
- ajout manuel via description ;
- ajout via photo.

## À construire

- écran complet de garde-robe ;
- édition/suppression ;
- statut possédé / wishlist ;
- photo d’item ;
- marque éventuelle ;
- taille ;
- saison ;
- couleur/coupe normalisées ;
- historique d’acquisition ;
- import de plusieurs pièces sur une photo ;
- onboarding optionnel « ajoute tes pièces les plus portées ».

## Réduction du cold start à moyen terme

- parsing de reçus ;
- lecture d’e-mails de confirmation ;
- import historique d’achats lorsque légalement/techniquement possible ;
- confirmation post-redirection « Tu l’as acheté ? » comme mécanisme minimal robuste.

---

# 10. Wishlist, attente et alertes

À ajouter après que Product Search fournisse de vrais produits.

Fonctions :

- mettre une option en favoris ;
- suivre son prix ;
- connaître l’impact budgétaire actuel ;
- alerter si :
  - le prix passe sous un seuil ;
  - le produit rentre dans le budget restant ;
  - une nouvelle enveloppe mensuelle s’ouvre ;
  - le stock revient si la source le permet.

La wishlist doit rester reliée au wallet, pas devenir une simple liste de produits.

---

# 11. Phasing intelligent — à sortir du stub

Aujourd’hui l’interface existe mais l’algorithme est illustratif.

Objectif futur : répartir les achats nécessaires sur plusieurs enveloppes en maximisant la valeur vestimentaire.

Exemple :

```text
Look complet = 170 €
Budget disponible = 100 €

Août
- pantalon : 45 €
- surchemise : 40 €

Septembre
- chaussures : 55 €
- accessoire : 30 €
```

Le moteur devra décider quelles pièces acheter en premier selon :

- réutilisabilité avec la garde-robe ;
- contribution au look ;
- urgence / saison ;
- prix ;
- disponibilité ;
- polyvalence ;
- préférences utilisateur.

---

# 12. Substitution intelligente — « version qui rentre »

L’autre moteur de H2 doit transformer un panier trop cher en proposition équivalente dans le budget.

À terme :

```text
look source : 189 €
reste budget : 78 €

→ version équivalente : 74 €
→ similarité de style : 84 %
→ 2 pièces déjà dans ta garde-robe
→ 1 seule pièce à acheter
```

Prérequis :

- Product Search réel ;
- embeddings / score de style ou règles robustes ;
- ranking budget-aware ;
- qualité suffisante pour ne pas détruire l’intention du look.

---

# 13. PurchaseScore — passer du stub au ranking réel

Le PurchaseScore devra classer les options selon une logique propre à Fashion Money, par exemple :

```text
PurchaseScore =
    style_match
  + wardrobe_complementarity
  + outfit_potential
  + budget_fit
  + price_value
  + user_preference
  - duplicate_penalty
```

Point stratégique : le produit **le moins cher** ne doit pas automatiquement être le meilleur choix.

Fashion Money doit être capable de préférer une pièce légèrement plus chère si elle :

- complète davantage la garde-robe ;
- permet beaucoup plus de tenues ;
- reste dans le budget ;
- évite un doublon ;
- correspond mieux au style de l’utilisateur.

---

# 14. Profil de style personnel

La Vision actuelle comprend le style d’une inspiration.

La prochaine couche IA pourra construire progressivement un **Style Profile** à partir de :

- captures analysées ;
- outfits sélectionnés ;
- produits favoris ;
- produits achetés ;
- produits rejetés ;
- garde-robe réelle ;
- couleurs dominantes ;
- coupes ;
- styles souvent choisis ;
- budget / comportement de décision.

Exemple de représentation future :

```text
style_profile
- smart casual: 0.82
- minimalist: 0.71
- old money/preppy: 0.68
- streetwear: 0.18

preferred_palette
- beige
- navy
- cream
- black
```

Ce profil ne doit pas enfermer l’utilisateur : il sert à personnaliser le ranking, pas à empêcher l’exploration.

---

# 15. Tenue du jour à partir de la garde-robe

Fonction initialement envisagée et toujours cohérente avec le produit mature :

> « construis-moi une tenue aujourd’hui uniquement avec ce que je possède ».

Entrées futures :

- garde-robe ;
- style souhaité ;
- occasion ;
- météo éventuellement ;
- préférences ;
- dernières tenues portées ;
- contraintes vestimentaires.

Sortie :

- outfit généré ;
- pièces réelles de la penderie ;
- éventuellement 0–1 achat facultatif pour compléter.

Le produit doit privilégier **réutiliser avant d’acheter**.

---

# 16. Nouvelle piste — Avatar / Digital Me / Virtual Try-On

Cette idée est désormais à intégrer dans la vision long terme du produit.

## 16.1 Deux niveaux possibles

### A. Avatar personnalisable

Alternative respectueuse de la vie privée :

- morphologie approximative ;
- taille ;
- teint ;
- cheveux ;
- silhouette ;
- avatar stylisé ou 3D.

Avantage : aucune photo personnelle obligatoire.

### B. Digital Me à partir de photos

L’utilisateur fournit quelques images de référence et Fashion Money génère une représentation qui lui ressemble davantage.

Pipeline cible :

```text
Outfit recommandé
        +
Photo / identité visuelle utilisateur
        ↓
Virtual Try-On
        ↓
« Cette tenue sur moi »
```

## 16.2 Positionnement recommandé

Ne pas commencer par construire un avatar 3D complexe.

La première version la plus cohérente serait probablement un **Virtual Try-On génératif 2D** :

```text
photo utilisateur
+ vêtements sélectionnés
→ rendu de la tenue portée
```

## 16.3 Pourquoi cela peut renforcer le moat

La visualisation ne serait pas isolée : elle resterait liée à la décision financière.

Exemple :

```text
Tenue A — avec ce que tu possèdes déjà
Coût : 0 €
[Essayer sur moi]

Tenue B — complète avec une pièce
Coût : 39 €
Solde après achat : 61 €
[Essayer sur moi]

Tenue C — version premium
Coût : 118 €
Dépasse ton budget
[Essayer sur moi]
```

Le try-on devient donc une **surface d’aide à la décision**, pas un gadget mode indépendant.

## 16.4 Prérequis avant développement

- Product Search réel ;
- outfit composition fiable ;
- stockage sécurisé des photos ;
- consentement explicite ;
- politique de suppression ;
- choix provider Virtual Try-On ;
- coûts d’inférence ;
- latency ;
- qualité visage/corps ;
- gestion de la confidentialité.

### Priorité

**Après Product Search + Outfit generation/ranking.**

---

# 17. Share-sheet depuis Instagram/TikTok

L’import galerie fonctionne, mais l’expérience cible reste :

```text
Instagram / TikTok / Pinterest / navigateur
        ↓ Partager
Fashion Money
        ↓
Analyse directe
```

À faire :

- share extension / share-sheet ;
- récupération de l’image ou de la capture lorsque possible ;
- fallback vers import local ;
- source analytics ;
- gestion des restrictions imposées par les apps tierces.

C’est un levier d’engagement important car **capture-first** doit rester le déclencheur fréquent.

---

# 18. Auth réelle, comptes et synchronisation

L’identité actuelle reste un stub de développement.

À faire avant bêta externe sérieuse :

- authentification ;
- compte utilisateur ;
- refresh tokens / sessions ;
- suppression de compte ;
- isolation stricte des données ;
- récupération de compte ;
- synchronisation multi-device ;
- politique de confidentialité ;
- export des données.

---

# 19. Analytics production et expérimentation

Le schéma d’événements existe ; le sink de production reste à choisir / brancher.

À construire :

- analytics SaaS réel ;
- dashboards H1–H4 ;
- funnel activation ;
- cohortes J+14/J+30 ;
- mesure `owned_pct` par `capture_index` ;
- tests A/B sur :
  - wording décision ;
  - tight threshold ;
  - rollover ;
  - phasing vs substitution ;
  - ranking produits ;
  - paywall.

---

# 20. Monétisation

Hypothèse H4 : le produit doit éviter de devenir structurellement dépendant d’un modèle qui pousse à acheter plus.

Direction actuelle :

- abonnement comme modèle principal potentiel ;
- affiliation éventuellement secondaire ;
- seconde-main compatible avec le message « acheter mieux » ;
- fonctionnalités avancées possibles dans un tier premium :
  - historique avancé ;
  - alertes ;
  - Digital Me / Try-On ;
  - suggestions tenues ;
  - analytics personnels ;
  - automatisation des reçus ;
  - planification vestimentaire.

Le modèle final doit être validé par données et non fixé uniquement par intuition.

---

# 21. Seconde-main / Europe / Vinted

Toujours dans la roadmap :

- intégrer la seconde-main dans les options ;
- permettre au ranking de préférer un article d’occasion pertinent ;
- comparer prix neuf / seconde-main ;
- adapter disponibilité et fraîcheur, car les articles uniques disparaissent vite.

Le cadre économique est plus cohérent avec la promesse anti-surconsommation qu’une affiliation exclusivement fast-fashion.

---

# 22. Reçus et e-mails de confirmation

Cible V2 déjà identifiée dans le PRD.

Objectif : réduire la friction de mise à jour du Wallet et de la garde-robe.

Pipeline possible :

```text
email / reçu
→ détection achat vêtements
→ extraction marchand / article / prix / date
→ confirmation utilisateur
→ WardrobeItem
→ SPEND
```

Toujours prévoir une confirmation utilisateur avant mutation automatique si la confiance est insuffisante.

---

# 23. Notifications utiles

À ajouter lorsque les objets métier existent réellement :

- prix sous seuil ;
- produit désormais compatible avec le budget ;
- ouverture de nouvelle enveloppe ;
- rappel d’un achat différé ;
- wishlist ;
- retour en stock ;
- décision non terminée.

Éviter les notifications qui encouragent artificiellement la consommation.

---

# 24. Documents actuels du repository qui doivent être mis à jour

Le repository contient actuellement six documents métier/tech principaux dans `docs/`, plus le `README.md`.

## 24.1 `README.md` — priorité HAUTE

### Obsolète actuellement

Le README indique encore notamment :

- slice `VS-01→05` comme dernier état ;
- `12/12` tests ;
- capture via share-sheet dans le diagramme alors que l’import galerie réel est aujourd’hui l’entrée implémentée ;
- Vision et Product Search présentés globalement comme providers à remplacer ;
- roadmap encore centrée sur Vague A / Vague B initiales.

### À mettre à jour

- PR #1→#8 ;
- mobile réel ;
- galerie réelle ;
- object storage réel ;
- Groq ;
- Qwen 3.8 ;
- contrat `outfits[]` ;
- Product Search comme prochain grand jalon ;
- statut réel des tests/CI ;
- nouvelle roadmap.

---

## 24.2 `docs/PRD-v1.md` — priorité HAUTE

Le PRD dit encore explicitement :

```text
feed social, essayage virtuel, styling pour le styling = hors V1
```

Cette décision reste correcte pour V1, mais il faut ajouter une section :

**« Post-V1 / Product Expansion »** avec :

- outfit selection ;
- profil de style ;
- tenue du jour ;
- Digital Me / Avatar ;
- Virtual Try-On ;
- wishlist budget-aware ;
- Product Search réel ;
- receipt ingestion.

Il faut aussi actualiser le modèle `Look/Capture` pour refléter :

```text
Capture → N outfits → N pieces
```

et non plus seulement `style + pieces[]`.

---

## 24.3 `docs/technical-design-v1.md` — priorité HAUTE

À actualiser avec les choix réellement implémentés :

- MinIO/object storage réel ;
- multipart upload ;
- `GroqDecompositionProvider` ;
- Qwen 3.8 comme provider actuel de dev ;
- schema collage-aware ;
- `category_raw` + normalisation ;
- `confidence` ;
- `representative_outfit_index` ;
- futur `selected_outfit_index` ;
- architecture Product Search à venir ;
- future frontière Virtual Try-On provider.

---

## 24.4 `docs/vertical-slice-1.md` — priorité HAUTE

Le document est toujours marqué :

```text
Statut : Draft
Vision et Product Search mockés
```

Or une grande partie du slice est terminée et Vision est devenue réelle.

À transformer en :

- backlog avec cases réellement cochées ;
- historique de jalons ;
- section `Post Vertical Slice 1` ;
- prochain slice : **Real Product Search** ;
- sélection outfit ;
- hardening Vision ;
- share-sheet ;
- bêta.

---

## 24.5 `docs/decisions-applied.md` — priorité MOYENNE/HAUTE

Ajouter les décisions architecturales prises depuis la fondation :

- provider-swappable réel ;
- object storage privé ;
- aucun secret dans Git ;
- Groq utilisé en développement ;
- Qwen 3.8 préféré à 3.6 après smoke test ;
- contrat Vision collage-aware ;
- garder `category_raw` + normaliser ;
- ne pas utiliser `material` comme gate dur ;
- ambiguity → sélection utilisateur plutôt que heuristique excessive ;
- ne pas construire Product Search par scraping multi-sites comme première approche.

---

## 24.6 `docs/vision-smoke-test.md` — priorité MOYENNE

Déjà beaucoup plus à jour, mais il faudra figer après PR #8 :

- résultat final Qwen 3.8 4/4 ;
- métriques finales ;
- ghost outfits ;
- conclusion officielle du gate ;
- décision « Vision validée pour passer à Product Search ».

---

## 24.7 `docs/wave-b-analytics.md` — priorité MOYENNE

À compléter avec les nouveaux événements :

- `image_uploaded` ;
- `vision_analysis_started` ;
- `vision_analysis_failed` ;
- `outfits_detected` ;
- `outfit_selected` ;
- futur `product_search_started/results_viewed` ;
- `merchant_redirected` ;
- `wishlist_added` ;
- `price_alert_triggered`.

---

# 25. Documents manquants à créer

Le README mentionne déjà plusieurs docs à créer. Ils deviennent maintenant utiles.

## `docs/ARCHITECTURE.md`

Vue actuelle réelle des composants et providers.

## `docs/DATA_MODEL.md`

Schéma source de vérité mis à jour avec :

- capture ;
- outfit ;
- piece ;
- selected outfit ;
- product candidates ;
- wishlist ;
- future avatar profile.

## `docs/DECISIONS.md`

ADRs / log chronologique des décisions produit/tech.

## `docs/TESTING.md`

Inclure :

- tests unitaires ;
- E2E ;
- CI ;
- smoke tests provider ;
- datasets privés ;
- critères de gate.

## `docs/ROADMAP.md`

Transformer la roadmap en jalons lisibles indépendamment des anciennes vagues.

## `CHANGELOG.md`

Historique par PR / version.

## `docs/PRODUCT-IDEAS.md` ou `docs/FUTURE.md`

Backlog d’idées non engagées :

- avatar ;
- Digital Me ;
- Virtual Try-On ;
- météo ;
- packing voyage ;
- capsules ;
- tenues selon occasion ;
- social éventuel ;
- styliste conversationnel ;
- challenges no-buy / budget ;
- analyse de doublons ;
- empreinte seconde-main / durabilité si pertinent.

Le but est d’éviter de polluer le PRD V1 avec des idées post-MVP tout en ne les perdant pas.

---

# 26. Roadmap recommandée à partir d’aujourd’hui

## Jalon 0 — Finaliser Vision

- [x] Upload réel ;
- [x] object storage ;
- [x] Groq provider ;
- [x] smoke test réel ;
- [x] collage-aware ;
- [x] normalisation ;
- [x] Qwen 3.8 4/4 ;
- [ ] finaliser CI PR #8 ;
- [ ] squash & merge PR #8 ;
- [ ] synchroniser les docs.

## Jalon 1 — Product Search réel

- [ ] benchmark providers ;
- [ ] contrat provider réel ;
- [ ] produits achetables ;
- [ ] prix ;
- [ ] liens marchands ;
- [ ] 3–5 résultats pertinents ;
- [ ] tests ;
- [ ] intégration Decision Engine.

## Jalon 2 — Multi-outfit UX

- [ ] sélectionner le look d’un collage ;
- [ ] stocker sélection ;
- [ ] analytics ;
- [ ] ignorer/neutraliser ghost outfits ;
- [ ] relancer matching/search sur l’outfit sélectionné.

## Jalon 3 — Product ranking / PurchaseScore réel

- [ ] budget fit ;
- [ ] complémentarité garde-robe ;
- [ ] style match ;
- [ ] duplicate penalty ;
- [ ] badge best réellement significatif.

## Jalon 4 — Garde-robe utilisable

- [ ] liste complète ;
- [ ] ajout photo ;
- [ ] édition ;
- [ ] suppression ;
- [ ] multi-item detection ;
- [ ] seeding onboarding.

## Jalon 5 — Wishlist budget-aware

- [ ] favoris ;
- [ ] impact wallet ;
- [ ] attente ;
- [ ] changement de prix ;
- [ ] notifications.

## Jalon 6 — Intelligent Phasing & Substitution

- [ ] moteur de phasing ;
- [ ] version ≤ budget ;
- [ ] H2 mesurable avec vrais produits.

## Jalon 7 — Share-sheet / capture frictionless

- [ ] partager depuis applications sociales ;
- [ ] traitement rapide ;
- [ ] analytics source.

## Jalon 8 — Bêta réelle

- [ ] auth ;
- [ ] analytics prod ;
- [ ] privacy ;
- [ ] logs/monitoring ;
- [ ] coûts providers ;
- [ ] utilisateurs test ;
- [ ] validation H1/H2/H3.

## Jalon 9 — Automatisation garde-robe

- [ ] reçus ;
- [ ] e-mails ;
- [ ] confirmation assistée ;
- [ ] import historique.

## Jalon 10 — Outfit Intelligence

- [ ] profil de style ;
- [ ] tenue du jour ;
- [ ] outfit generation ;
- [ ] réutilisation maximale de la penderie ;
- [ ] contexte occasion / météo si pertinent.

## Jalon 11 — Digital Me / Virtual Try-On

- [ ] avatar simple ;
- [ ] option photo-based ;
- [ ] consentement ;
- [ ] provider try-on ;
- [ ] rendu « essayer sur moi » ;
- [ ] intégration à la décision budget.

## Jalon 12 — H4 / monétisation

- [ ] paywall ;
- [ ] abonnement ;
- [ ] tiers avancé ;
- [ ] mesurer willingness-to-pay ;
- [ ] affiliation seconde-main éventuellement.

---

# 27. Idées supplémentaires cohérentes à garder dans le backlog

Ces idées ne doivent pas toutes devenir des features, mais elles sont cohérentes avec la donnée que Fashion Money accumulera.

### Packing / voyage

> « Je pars 5 jours à Tirana, crée 7 looks avec ma valise et dis-moi s’il manque une pièce. »

### Capsule wardrobe

> « Quelle est la plus petite liste d’achats qui me permet de produire 15 nouvelles tenues ? »

### Anti-doublon intelligent

> « Tu as déjà deux pantalons très proches de celui-ci. »

### Cost-per-wear secondaire

Pas comme fonction héroïque, mais utile pour enrichir le PurchaseScore une fois l’historique réel disponible.

### Budget adaptatif

L’app peut suggérer un budget, mais ne doit jamais le modifier silencieusement.

### Stylist conversationnel

> « J’ai un dîner vendredi, donne-moi 3 tenues avec ce que je possède et maximum 40 € d’achat supplémentaire. »

### Wardrobe health

Détecter :

- catégories surreprésentées ;
- couleurs redondantes ;
- manque de basiques ;
- pièces peu combinables.

### Outfit memory

Historiser les tenues portées afin d’éviter de recommander toujours les mêmes combinaisons.

### Occasion Engine

Travail, date, mariage, voyage, casual, entretien, soirée, etc.

### « No-buy mode »

Pour un mois où l’utilisateur fixe `shopping_budget = 0`, Fashion Money devient uniquement un moteur de réutilisation de garde-robe.

Cette fonction est particulièrement alignée avec le positionnement « acheter mieux, pas plus ».

---

# 28. Principes à ne pas perdre pendant l’élargissement

1. **Le solde après achat reste visible avant la décision.**
2. **Le Wallet reste source de vérité serveur.**
3. **La Vision ne devient pas le moat.**
4. **Le Product Search ne doit pas dicter le produit.**
5. **Réutiliser la garde-robe avant de pousser un achat.**
6. **Une recommandation doit pouvoir être expliquée.**
7. **Un provider externe doit rester remplaçable.**
8. **Ne jamais committer de secrets ni de photos utilisateurs privées.**
9. **Une incertitude explicite vaut mieux qu’un attribut halluciné.**
10. **L’avatar / try-on doit aider à décider, pas détourner Fashion Money vers une app de mode générique.**

---

# 29. Prochaine action concrète

Ordre recommandé immédiatement :

```text
1. Vérifier la CI finale de la PR #8
2. Squash & merge PR #8
3. Mettre README + docs structurants à jour
4. Créer / mettre à jour ROADMAP
5. Ouvrir le jalon Product Search réel
6. Ajouter l’écran de sélection d’outfit pendant ce jalon
```

À ce stade, Fashion Money disposera du pipeline :

```text
vraie image
→ vraie Vision
→ vrai outfit
→ vraie pièce manquante
→ vrai produit achetable
→ vraie décision budgétaire
```

Ce sera le prochain passage important : le produit ne démontrera plus seulement son architecture, mais commencera à démontrer sa **proposition de valeur complète sur des données réelles**.

# Product Search réel — benchmark et choix de stratégie

> **Date :** 27 août 2026 · **Statut :** décision de travail pour PR #10
> **Amont :** #8 (Vision collage-aware) et #9 (sélection d'outfit) mergées · **Aval :** contrat Product Search + benchmark provider réel
> **Méthode :** comparaison des réseaux d'affiliation FR/EU, APIs de recherche temps réel, seconde main et Shopify Global Catalog.

---

## 1. Critère structurant

Fashion Money affirme, avant l'achat, une phrase engageante : *« il te restera 61 € »*. Cette phrase n'a de valeur que si le prix utilisé est réel, encore valide au moment de la décision, et rattaché à une URL marchande réellement achetable.

Le critère structurant n'est donc pas la taille brute du catalogue mais : **la source permet-elle de découvrir un produit pertinent puis de vérifier un prix engageable et sa disponibilité avant `/decisions/evaluate` ?**

Cette exigence est plus importante que le coût par requête, la couverture brute ou le nombre de résultats.

---

## 2. Sources écartées du chemin critique

### APIs SERP Google Shopping

SerpApi, SearchApi.io, Scale SERP, Zenserp, Bright Data et Oxylabs restent utiles pour du prototypage, de la veille ou du fallback de couverture. Elles ne sont pas retenues comme provider P0 du chemin critique financier.

Le résultat Shopping standard expose d'abord un produit Google ; obtenir un vendeur et une URL marchande directe peut nécessiter un second appel. L'absence d'un contrat fort de disponibilité et la dépendance au scraping en font une base moins adaptée à la promesse financière de Fashion Money.

### Amazon

À revisiter plus tard. L'accès programme/API impose un amorçage et le catalogue mode n'est pas prioritaire pour notre positionnement.

### Autres pistes non retenues immédiatement

Apify est trop coûteux comme socle, ShopStyle Collective est fermé, Google Content API for Shopping et Bing Shopping ne constituent plus une voie de recherche utilisable, et le Zalando Partner Program vise les vendeurs marketplace plutôt que l'accès catalogue côté publisher.

---

## 3. Sources retenues

### Shopify Global Catalog — P0 de benchmark

Le Shopify Global Catalog est désormais notre **premier provider à benchmarker**, pas nécessairement notre socle long terme.

Points forts :

- recherche plein texte inter-marchands sur l'écosystème Shopify ;
- variantes, disponibilité et médias ;
- prix structurés ;
- contexte de destination et de devise ;
- possibilité de récupérer un `checkout_url` au niveau variante ;
- absence de clé API ou de bearer token classique.

#### Prérequis UCP

« Sans API key » ne signifie pas « sans prérequis ». Chaque requête doit inclure un `meta.ucp-agent.profile` pointant vers **une URL publique résolvable décrivant le profil UCP de l'agent**.

Conséquence : la landing page / le domaine Fashion Money devient un prérequis technique du benchmark Shopify. La même surface servira aussi aux inscriptions réseaux, à la politique de confidentialité, aux mentions légales et à la présentation produit.

#### Vocabulaire

Shopify n'est pas aussi aligné que les feeds Awin avec notre Matching Engine. Les attributs directement poussables dans `search_catalog` sont principalement **Color, Size et Target gender**. `cut` et `material` restent surtout du contexte de requête/re-scoring et ne doivent pas être supposés structurés.

Donc : **Shopify = accélérateur de validation ; Awin = meilleur candidat au socle mode long terme.**

#### Prix en unités mineures

`price.max` est exprimé en unités mineures. Un budget de 100 € doit donc devenir `10000`, jamais `100`.

Le harness doit vérifier explicitement que le filtre de prix est interprété dans la devise utilisateur (`EUR` pour la France) et non silencieusement en USD.

#### `product_url` ≠ `checkout_url`

Un `checkout_url` Shopify est un panier/checkout pré-rempli au niveau variante. Ce n'est pas la même expérience qu'une page produit.

Fashion Money doit conserver les deux champs séparément pour que l'arbitrage reste réversible :

- `product_url` : fiche produit / redirection marchande ;
- `checkout_url` : accélérateur éventuel de conversion, optionnel.

Le choix d'utiliser ou non le checkout direct doit être décidé explicitement dans `decisions-applied.md`. Il ne doit jamais être adopté par accident d'implémentation.

### Tradedoubler — P1, premier réseau de recherche live

Tradedoubler reste la meilleure voie de repli et le premier réseau affilié à brancher après le benchmark Shopify.

L'API de recherche produit permet requête texte, filtres de prix, marque, condition, disponibilité, tri et pagination. Elle renvoie une URL produit trackée, prix + devise, image, disponibilité, stock, taille, marque et date `modified`.

Réserve : `fid` impose d'être approuvé sur au moins un programme marchand pertinent. HTTPS doit être confirmé avant tout usage de token en production.

### Awin — P2 et socle catalogue long terme

Awin conserve la meilleure adéquation de vocabulaire avec notre moat : `colour`, `size`, `material`, `pattern`, `brand_name`, `in_stock`, prix, images et deep links trackés.

Ces champs s'alignent directement sur notre matching `category / color / cut / material` et réduisent la quantité de parsing/sémantique à reconstruire.

Limite : Awin fournit principalement des feeds à ingérer/indexer, pas un moteur de recherche live interrogeable. Il faudra donc construire un index local (Postgres FTS, Meilisearch ou Typesense).

Pour la France, le dépôt d'inscription publisher est **1 €**, remboursé au premier paiement.

### eBay Browse — P3, couche seconde main

Temps réel, `EBAY_FR`, conditions d'occasion structurées, prix et `itemAffiliateWebUrl`. À intégrer après le premier provider neuf.

Le quota standard de Browse est de 5 000 appels/jour ; une augmentation devra être demandée si la bêta prend du volume.

### Vinted — deep-link uniquement

Pas d'API catalogue publique adaptée et pas de scraping. Le bon produit est un bouton : **« Chercher aussi sur Vinted »** vers une URL de recherche préremplie, sans stockage ni ingestion de données Vinted.

---

## 4. Classement révisé

| Rang | Source | Rôle | Quand |
|---|---|---|---|
| P0 | **Shopify Global Catalog** | Smoke test réel, recherche inter-marchands | Immédiat après profil UCP public |
| P1 | **Tradedoubler** | Premier réseau de recherche live | En parallèle des inscriptions |
| P2 | **Awin** | Socle mode riche, indexé localement | Semaines suivantes |
| P3 | **eBay Browse** | Seconde main | Après premier jalon neuf |
| Bonus | **Vinted** | Deep-link de recherche sortant | Dès que l'écran options le permet |
| Backup | **SERP Google Shopping** | Benchmark/veille/couverture | Hors chemin financier critique |

Le couple stratégique est désormais : **Shopify pour valider vite → Tradedoubler pour la recherche réseau → Awin pour la profondeur structurée → eBay pour l'occasion.**

---

## 5. Fraîcheur du prix : invariant produit

Le risque principal n'est pas de manquer un produit, mais d'annoncer un solde après achat sur un prix périmé.

L'architecture doit donc séparer :

```text
DÉCOUVERTE                          ENGAGEMENT
search()/index local                verify() sur UNE option
3–5 candidats                       prix + disponibilité revérifiés
prix indicatif + fetched_at         prix engagé pour la décision
        │                                  │
        └──── utilisateur choisit ─────────┘
```

On ne revalide jamais tous les candidats : uniquement celui que l'utilisateur s'apprête à envoyer vers `/decisions/evaluate`.

Corollaires :

1. chaque prix de découverte porte `fetched_at` ;
2. si `verify()` révèle un changement, l'UI l'affiche avant le verdict ;
3. les TTL seront différenciés : neuf plus long, occasion plus court, pièce unique très courte.

---

## 6. Contrat provider cible

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SearchContext:
    piece: LookPiece
    outfit_style: str | None
    dominant_palette: list[str]
    budget_available: float | None
    ship_to: str = "FR"
    currency: str = "EUR"


@dataclass(frozen=True)
class ProductCandidate:
    provider: str
    external_id: str
    variant_id: str | None

    name: str
    raw_category: str | None

    price: float
    original_price: float | None
    shipping_price: float | None
    currency: str

    merchant: str
    brand: str | None

    product_url: str
    checkout_url: str | None
    image_url: str | None

    availability: str | None
    size: str | None
    color: str | None
    material: str | None
    condition: str = "new"

    fetched_at: datetime
    expires_at: datetime | None


class ProductSearchProvider(Protocol):
    def search(self, ctx: SearchContext, limit: int = 5) -> list[ProductCandidate]: ...

    def verify(self, candidate: ProductCandidate) -> ProductCandidate | None: ...
```

Décisions importantes :

- devise jamais implicite ;
- budget réellement transmis au provider ;
- style de l'outfit et palette traversent le port ;
- `condition` existe dès V1 pour ouvrir eBay plus tard ;
- `product_url` et `checkout_url` sont distincts ;
- `variant_id` est conservé pour prix/stock/taille/couleur au niveau variante ;
- `verify()` est une primitive du contrat, pas un patch tardif.

---

## 7. Landing page et chemin administratif

Les inscriptions réseau ne doivent pas bloquer le code, mais la landing page Fashion Money devient une tâche immédiate pour trois raisons :

1. héberger le profil UCP public requis par Shopify ;
2. présenter une surface crédible aux réseaux d'affiliation ;
3. porter politique de confidentialité, mentions légales et mentions de liens commerciaux.

Awin accepte aussi des publishers basés sur des réseaux sociaux ; la landing page n'est donc pas une obligation universelle de tous les réseaux. Ici elle devient surtout une **infrastructure commune produit + conformité + Shopify**.

Les inscriptions Tradedoubler et Awin doivent démarrer en parallèle du développement de la PR #10.

---

## 8. Gate du benchmark provider

Même discipline que le smoke test Vision : le provider P0 n'est pas choisi sur impression, mais sur le corpus réel produit par Qwen 3.8.

Pour chaque pièce normalisée issue des quatre collages de référence :

| Signal | Seuil / mesure |
|---|---|
| Pièces donnant ≥3 résultats plausiblement portables | ≥ 80 % |
| Écart prix source vs page/verify | ≤ 2 % |
| Résultats avec image exploitable | ≥ 90 % |
| Résultats avec disponibilité renseignée | ≥ 70 % |
| Présence de size/color | mesurer |
| Latence p95 `search()` | ≤ 800 ms |
| Latence p95 `verify()` | ≤ 500 ms |
| Devise appliquée au filtre budget | 100 % correcte |
| Prix médian des candidats / budget mensuel type | **à mesurer explicitement** |

### Gate prix/budget

Un provider peut avoir une excellente couverture et rester inutilisable si son catalogue est systématiquement trop cher.

Le harness doit donc calculer au minimum :

```text
median_candidate_price
median_candidate_price / monthly_budget
share_candidates_price_lte_budget
```

Avec le scénario J0 de référence à **100 €/mois**, une source dont le candidat médian dépasse largement l'enveloppe doit être considérée comme mal adaptée, même si la pertinence stylistique est bonne.

### Gate de dérive de prix

Le harness doit également mesurer ce qui justifie la séparation `search()` / `verify()` :

- revalidation à H+1 ;
- revalidation à H+6 ;
- revalidation à H+24 ;
- taux de variation de prix ;
- amplitude médiane/p95 de variation ;
- taux de produits devenus indisponibles.

Ces mesures permettront ensuite de fixer les TTL sur des données plutôt que par intuition.

### Signal qualitatif

Dernier gate non automatisable : **est-ce qu'un utilisateur cible porterait réellement les trois articles proposés ?**

Un candidat techniquement proche mais esthétiquement mauvais est un échec produit.

---

## 9. Décisions ouvertes avant code complet

1. **FR uniquement au départ** — recommandation actuelle : oui.
2. **Neuf seul en première intégration** — oui pour P0/P1 ; le contrat reste prêt pour l'occasion.
3. **Usage du checkout Shopify** — décision explicite à inscrire dans `decisions-applied.md` ; ne pas utiliser automatiquement.
4. **Profil UCP** — définir et héberger l'URL publique avant le smoke test Shopify.
5. **ToS redistribution/cache** — obtenir les clauses réseau par écrit avant production, surtout pour Awin/Tradedoubler.
6. **Provider final P0** — ne le figer qu'après benchmark réel France.

---

## 10. Plan PR #10

La PR #10 doit rester centrée sur le **contrat + harness**, pas sur PurchaseScore.

Périmètre :

1. introduire `SearchContext` ;
2. enrichir `ProductCandidate` ;
3. ajouter `search()` + `verify()` ;
4. maintenir le mock compatible ;
5. ajouter un `ShopifyGlobalCatalogProvider` expérimental ;
6. ajouter le harness de benchmark ;
7. mesurer couverture, qualité, prix/budget, latence et fraîcheur ;
8. ne pas modifier PurchaseScore dans cette PR ;
9. ne pas introduire encore Awin/Tradedoubler dans le chemin critique.

Gate de sortie : **données suffisantes pour confirmer Shopify P0 ou basculer proprement sur Tradedoubler sans changer le contrat.**

---

## Sources

### Réseaux d'affiliation

- Awin — Product Feed Intro
- Awin — Enhanced Google Feeds API
- Awin — Column descriptions / hosting feeds
- Awin — Application process / FAQ France
- Tradedoubler — Publisher Products API
- CJ — Product Search API
- Rakuten — Product Search API / Catalog feeds
- Kwanko — Product feeds
- Effinity — Gestion de flux produits
- Skimlinks — Merchant API

### APIs de recherche / commerce

- Shopify — Global Catalog / UCP
- Universal Commerce Protocol (UCP)
- SerpApi — Google Shopping / Product API
- SearchApi.io
- Bright Data SERP API
- Oxylabs Google Shopping Search

### Seconde main

- eBay Browse API
- eBay Condition ID values
- eBay Application Growth Check
- eBay Partner Network
- Vinted Pro Integrations / robots.txt
- Label Emmaüs / Affilae

### Cadre légal FR

- Loi française sur l'influence commerciale et obligations de transparence applicables aux liens commerciaux.

---

### Points à qualifier empiriquement ou par contact direct

- couverture géographique réelle France du Shopify Global Catalog ;
- comportement exact de `price.max` avec `currency=EUR` et destination FR ;
- rate limits et conditions d'usage Shopify Global Catalog ;
- qualité mode/DTC réelle sur les requêtes Qwen 3.8 ;
- clauses ToS de redistribution/cache chez Awin et Tradedoubler ;
- couverture marchands mode disponible après approbation réseau.

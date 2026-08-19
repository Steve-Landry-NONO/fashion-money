# Technical Design / Architecture V1 — Money layer for your wardrobe

> **Statut :** Draft · **Version :** 1.0 · **Date :** 18 août 2026
> **Amont :** teardown → wedge → proto v0.1 → proto v0.2 → one-pager MVP → **PRD V1** → *ce document*
> **But :** figer le système (pas le produit) pour pouvoir découper epics et tickets. Traduit les décisions du PRD, ne les rediscute pas.

## 0. Principes d'ingénierie
1. **Acheter la commodité, construire le moat.** On n'écrit pas ce qui existe mieux ailleurs (vision, recherche produit, auth, analytics infra) ; on écrit ce qui nous différencie (Wallet, Decision, Matching).
2. **Interfaces stables sur inconnues.** Phasing et Substitution ont un contrat d'I/O figé ; leur algorithme est un *plugin* remplaçable (cf. PRD §9) — on peut changer l'intérieur sans toucher aux appelants ni casser l'instrumentation H2.
3. **Instrument-first.** Aucun parcours n'est « fini » sans ses événements analytics (PRD §7).
4. **Monolithe modulaire, pas microservices.** Un backend, des modules à frontières nettes. On n'extrait un service que si une contrainte réelle l'exige.
5. **Déterminisme financier.** Le Wallet est un **ledger append-only** ; le solde est dérivé, jamais muté à la main.

## 1. Frontière Build vs Buy *(l'épine dorsale)*

| Capacité | Build / Buy | Pourquoi | Choix / candidats V1 |
|---|---|---|---|
| Décomposition de look (image → style + pièces) | **BUY** | Commodité ; Google/fournisseurs font mieux. | API vision fashion / modèle multimodal, derrière `DecompositionProvider`. |
| Recherche produit + prix (« similaires achetables ») | **BUY / INTEGRATE** | Catalogue mondial impossible à répliquer ; exact-match reste faible → viser *similaire*. | Moteur Lens-class + réseaux d'affiliation, derrière `ProductSearchProvider`. |
| **Matching garde-robe** (possédé vs look, anti-doublon) | **BUILD** | Adjacent au moat ; logique propriétaire. | Similarité par attributs (+ embeddings optionnels du provider vision). |
| **Decision Engine** (verdict + issues + PurchaseScore) | **BUILD** | **C'est le produit.** | Service déterministe, config externalisée. |
| **Wallet Engine** (enveloppe, report, solde) | **BUILD** | **C'est le moat.** Déjà éprouvé (voir §3.3). | Ledger + job de report mensuel. |
| Phasing / Substitution | **BUILD (plus tard)** | Inconnues mesurées (H2). | V1 = stub derrière interface. |
| Auth / comptes | **BUY** | Aucune valeur à réécrire. | Auth managé (email + social). |
| Analytics (collecte/pipeline) | **BUY** (+ schéma maison) | Infra commodité ; le *schéma d'événements* est à nous. | SaaS analytics produit + miroir entrepôt. |
| Stockage images (captures) | **BUY** | Object storage standard. | S3-compatible (MinIO self-host possible). |
| Paiement | **NI L'UN NI L'AUTRE (V1)** | On **redirige** vers le marchand → **hors périmètre PCI**. | Aucun traitement de paiement en V1. |
| Notifications / e-mail | **BUY** | Commodité. | Provider push + e-mail transactionnel. |

**Ligne à retenir :** on construit **Wallet + Decision + Matching + l'app** ; on achète **Vision + Recherche produit + Auth + Analytics infra + Stockage + Notifications**.

## 2. Vue d'ensemble

```
        ┌──────────────────────────────┐
        │   App mobile (Expo/RN)        │   Share-target iOS/Android (capture depuis TikTok/Insta)
        │   + Web companion (léger)     │
        └───────────────┬──────────────┘
                        │ REST/HTTPS (BFF)
        ┌───────────────▼──────────────┐
        │        Backend (monolithe modulaire)         │
        │  ┌────────┐ ┌──────────┐ ┌───────────────┐   │
        │  │ Wallet │ │ Decision │ │   Matching    │   │  ← BUILD (moat)
        │  │ Engine │ │  Engine  │ │    Engine     │   │
        │  └────────┘ └──────────┘ └───────────────┘   │
        │  Adapters (ports & adapters) ───────────────►│──► Vision provider   (BUY)
        │  Capture pipeline (async jobs) ─────────────►│──► ProductSearch      (BUY)
        │  Analytics emitter ─────────────────────────►│──► Analytics SaaS     (BUY)
        └───────┬───────────────┬──────────────────────┘
                │               │
         ┌──────▼─────┐   ┌─────▼──────┐        ┌────────────────┐
         │ PostgreSQL │   │ Object     │        │ Auth managé     │ (BUY)
         │ (+ ledger) │   │ storage    │        └────────────────┘
         └────────────┘   └────────────┘
```

## 3. Composants

### 3.1 Clients
- **Mobile-first, cross-platform : Expo / React Native.** Justification : le **share-target natif** (importer une capture depuis TikTok/Insta) est central et nécessite des extensions natives iOS/Android — RN les couvre, et **c'est ta stack éprouvée sur S&S Budget** (Flutter reste dans ta boîte à outils via LMF, mais le précédent le plus proche est RN). 
- **Web companion léger** V1 : marketing + reprise de session, pas le parcours complet (le geste « capture » est mobile).
- Le client ne contient **aucune règle métier financière** : verdict, solde, report viennent du backend (source de vérité unique).

### 3.2 Backend
- **Monolithe modulaire**, modules à frontières explicites : `wallet`, `decision`, `matching`, `capture`, `catalog` (adapters providers), `analytics`, `identity`.
- **API REST** (BFF) — ressources claires + un endpoint « évaluer une décision ». Pas de GraphQL en V1 (surdimensionné).
- **Langage :** deux options réelles selon la priorité :
  - **FastAPI (Python) + PostgreSQL** — *recommandé* : aligné sur la trajectoire data/ML (embeddings de matching, scoring de décision, analyses H1–H4) et sur ton expérience FastAPI (PI Dataset Builder).
  - **Node/Express + Postgres** — continuité directe avec S&S Budget si le time-to-beta prime.
  - Quel que soit le choix, le **Wallet Engine est portable depuis S&S Budget** (mêmes primitives).

### 3.3 Wallet Engine  *(BUILD — moat, déjà éprouvé)*
- **Réutilise le pattern de S&S Budget** : caisses/enveloppes, reports mensuels automatiques, soldes réel/prévisionnel. On les transpose en une enveloppe *shopping vêtements*.
- **Modèle ledger append-only** : chaque mouvement (dépense, ajustement, report) est une ligne immuable ; `available` est **dérivé**, jamais écrit directement. Auditable, et rend le report déterministe.
- **Règles (PRD §6.1)** : base mensuelle configurable ; reset au 1er ; report du non-dépensé plafonné à 1× la base ; modif de base effective période suivante.
- **Job de report** : tâche planifiée mensuelle qui écrit une ligne `rollover_in = min(available_fin_mois, cap)` et ouvre la période.
- **Atomicité** : la confirmation d'achat (débit + ajout garde-robe) est **une transaction**.
- ⚠️ **Différence avec S&S** : S&S est self-host/LAN/Tailscale pour un foyer ; ici c'est **multi-tenant hébergé** pour des utilisateurs publics. Le *pattern* se réutilise, pas le déploiement.

### 3.4 Decision Engine  *(BUILD — le produit)*
- **Fonction pure** : `evaluate(available, option, wardrobe_ctx, config) → { verdict, available_after, issues[], purchase_score }`.
- **Verdict (PRD §6.4.1)** : `over` si `available_after < 0` ; `tight` si `0 ≤ available_after < tight_threshold` ; `fits` sinon. `tight_threshold = max(15€, 15% × base)` — **config externalisée** (paramètre à apprendre, pas à débattre).
- **Issues** : `fits/tight` → acheter (+ alternatives) ; `over` → **étaler** ET **substituer** à parité (pré-requis H2) + attendre / recréer.
- **Phasing & Substitution = plugins** : interfaces `PhasingStrategy` et `SubstitutionStrategy` avec I/O figé ; **implémentation V1 = stub** (split illustratif / panier fictif). L'algorithme est hors-scope mais l'événement (`plan_created`, `substitution_selected`) est émis → H2 mesurable dès la bêta.
- **PurchaseScore** : `f(style_match, wardrobe_complementarity, outfit_potential, budget_fit, price_value, user_pref)` → **classe** les options et pose le badge « meilleure pour ta penderie ». Pondération TBD ; ce n'est **pas** le gate (le gate = budget).

### 3.5 Matching Engine  *(BUILD)*
- Représente pièces du look et items possédés en **vecteurs d'attributs** (catégorie, couleur, coupe, matière), + **embeddings optionnels** issus du provider vision.
- Sortie : `owned%` par pièce, `score_look = possédées / total`, flag **anti-doublon** si similarité à un item possédé > 80 %.
- V1 acceptable en attribut-based ; l'embedding est une amélioration derrière la même interface.
- **J0** : renvoie explicitement 0 % (jamais de faux score).

### 3.6 Capture pipeline
- Upload image → **object storage** (référence en base) → job **asynchrone** `DecompositionProvider` → persistance `look_pieces`.
- **Cache par hash d'image** (coût vision maîtrisé, captures dupliquées).
- **Privacy** : une capture peut contenir visages/pseudos → stockage minimal, suppression sur demande, rétention courte configurable (voir §6).

### 3.7 Providers (ports & adapters)
- `DecompositionProvider.decompose(image) → { style, pieces[] }`.
- `ProductSearchProvider.search({attributes, budget, ship_to}) → options[]` (`price`, `merchant`, `affiliate_url`, `similarity`).
- **Conçu pour le *similaire*, pas l'exact** (le exact-match/live-stock reste faible en 2026). Cache des résultats ; dégradation propre si le provider tombe.

## 4. Modèle de données (Postgres, essentiel)

```
users(id, auth_ref, region, created_at)
budget_config(user_id, base_amount, rollover_cap, period_type='calendar_month', updated_at)
budget_ledger(id, user_id, period, type[SPEND|ADJUST|ROLLOVER_IN], amount, ref_purchase_id?, created_at)   -- append-only
wardrobe_items(id, user_id, category, color, cut, material, price?, source[PHOTO|RECEIPT|PURCHASE], acquired_at)
captures(id, user_id, image_ref, status, created_at)               -- image_ref → object storage
looks(id, capture_id, style)
look_pieces(id, look_id, category, color, cut, material, swatch)
matches(look_piece_id, wardrobe_item_id?, owned_pct, is_owned)     -- résultat du Matching
options(id, look_piece_id, price, merchant, affiliate_url, similarity, purchase_score)
decisions(id, user_id, look_id, option_id?, verdict, available_at, price, issue, created_at)
purchases(id, user_id, option_id, price, confirmed_at, wardrobe_item_id)
```
- `available` **n'est pas stockée** : `available = base + Σ(ROLLOVER_IN) − Σ(SPEND) + Σ(ADJUST)` sur la période.
- Analytics : émis vers le SaaS ; **miroir optionnel** dans une table `events` / entrepôt pour l'analyse H1–H4 en propre.

## 5. Contrats API (extraits clés)

```
POST /budget                 { base_amount, rollover_cap }            → 200 { config }
GET  /wallet                 → { base, rollover_in, spent, available, period }

POST /captures               (multipart image)                        → 202 { capture_id, status:"processing" }
GET  /looks/{id}             → { style, pieces:[{id,category,attrs,owned_pct,is_owned}], score_look }
GET  /looks/{id}/gaps        → { missing:[look_piece_id...] }
GET  /gaps/{pieceId}/options → { options:[{id,price,merchant,similarity,purchase_score,is_best}] }

POST /decisions/evaluate     { option_id }                            → {
    verdict: "fits|tight|over",
    available, available_after, price,
    issues: [ {type:"buy"}, {type:"phase", plan?}, {type:"substitute", bundle?},
              {type:"wait"}, {type:"recreate"} ]
}

POST /purchases/confirm      { option_id }                            → 200 {
    purchase_id, wardrobe_item_id, wallet:{ spent, available }        -- transaction atomique
}
POST /wardrobe/items         { category, attrs, price?, source }      → { item }
GET  /wardrobe               → { items:[...], count }
```
- `/decisions/evaluate` est **sans effet de bord** (n'écrit pas de dépense) ; seule `/purchases/confirm` débite. Cohérent avec « `decision_viewed` ≠ activation » (PRD §7).

## 6. Transverses
- **Config & flags** : `tight_threshold`, `rollover_cap`, pondérations PurchaseScore → externalisés (feature flags / table config), modifiables sans redéploiement.
- **GDPR / EU** (utilisateurs FR/EU) : données et images en **région EU** ; minimisation des captures ; **suppression de compte + purge images** ; base légale claire.
- **Sécurité** : pas de paiement → pas de scope PCI en V1 ; secrets providers côté serveur ; rate-limit sur capture/search (coût).
- **Observabilité** : logs structurés, traces sur le pipeline capture, métriques de coût par appel provider.
- **Déploiement** : **Docker Compose** pour dev et parité self-host (aligné sur tes préférences : Linux, Compose, VM minimales) ; Postgres + MinIO conteneurisés ; passage à un hébergement managé pour la bêta publique (multi-tenant).
- **Résilience providers** : timeouts, retries, dégradation (« look non reconnu, réessaie » ; options indisponibles → message d'action).

## 7. Du système aux epics (bridge vers le découpage)
1. **Identity & Onboarding** — auth managé, set budget de base (`↳ H1/H4`).
2. **Wallet Engine** — ledger, dérivation `available`, job de report, confirmation atomique (`↳ H1`). *Accélérable via S&S Budget.*
3. **Capture pipeline** — upload, storage, job décomposition, cache hash (`↳ commodité`).
4. **Matching Engine** — attributs (+ embeddings), owned%, anti-doublon, état J0 (`↳ H3`).
5. **Catalog / ProductSearch integration** — adapter, cache, affiliation, similaire-not-exact (`↳ commodité`).
6. **Decision Engine** — verdict, issues, PurchaseScore, plugins Phasing/Substitution en stub (`↳ H1/H2`).
7. **Confirmation & loop closure** — purchase confirm, wardrobe+budget en une transaction (`↳ H3`).
8. **Analytics instrumentation** — schéma d'événements (PRD §7), funnel d'activation, miroir entrepôt (`↳ H1–H4`).
9. **Flows J0 / mature** — parcours + états vides + seeding skippable (`↳ H1/H3`).
10. **Config & flags** — seuils et pondérations paramétrables (`↳ apprentissage bêta`).

## 8. Décisions techniques laissées ouvertes (à confirmer)
- Backend **FastAPI** (trajectoire data/ML) vs **Node/Express** (continuité S&S) — trancher avant l'epic 2.
- Fournisseur **vision** et **recherche produit** — shortlister/benchmarker (coût, EU, qualité de décomposition) ; ne pas se lier avant un test.
- Matching **attribut-based seul** vs **+ embeddings** en V1 (dépend du provider vision retenu).
- Entrepôt analytics propre dès V1 ou miroir différé.
```
```

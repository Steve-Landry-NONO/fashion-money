# Vertical Slice 1 — Backlog d'implémentation

> **Statut :** Draft · **Version :** 1.0 · **Date :** 18 août 2026
> **Amont :** … → PRD V1 → Technical Design V1 → *ce backlog*
> **Stack figée :** Expo/RN · FastAPI/Python · PostgreSQL · object storage S3-compat · monolithe modulaire + ports/adapters · analytics SaaS · pas de checkout.

## But du slice
Faire tourner **le moat de bout en bout** — Wallet + Decision + Matching — sur un vrai backend, une vraie base et de vrais événements, avec **Vision et Product Search mockés**. Cible : reproduire le scénario du prototype v0.2 (régimes J0 et mature) contre l'API, puis remplacer les mocks par les providers réels sans toucher aux appelants.

## Périmètre
**Dans le slice (réel) :** Wallet Engine (ledger), Decision Engine (verdict + issues + stubs phasing/substitution), Matching attribut-based, confirmation atomique, schéma d'événements, client RN reproduisant la boucle.
**Mocké :** `DecompositionProvider` (retourne le look fixe v0.2), `ProductSearchProvider` (retourne les 3 options fixes).
**Hors slice :** vraies API vision/produit, embeddings, auth complète (stub dev), web, phasing/substitution *intelligents*, entrepôt analytics, notifications, paywall.

## Definition of Done — globale (héritée par chaque ticket)
- [ ] Code + **tests unitaires** pour toute logique d'engine ; lint + type-check + CI verts.
- [ ] Endpoints exposés en **OpenAPI** (auto FastAPI).
- [ ] **Événements analytics** émis là où spécifié, conformes au schéma PRD §7.
- [ ] **Migrations réversibles** ; aucun pas manuel en base.
- [ ] `docker compose up` depuis un checkout propre fait tourner l'ensemble.
- [ ] **Aucune règle financière côté client** (solde/verdict/report viennent du backend).
- [ ] Critères d'acceptation du ticket remplis et **démontrables**.

---

## E0 — Foundation
**US :** en tant que dev, je veux un socle reproductible pour construire les engines.
- **VS-01 · Scaffold + Compose.** FastAPI + `docker-compose` (api, postgres, minio) + lint/type/test/CI.
  *AC :* `docker compose up` sert `/health` ; pipeline CI verte sur push.
- **VS-02 · Migrations + schéma de base (Alembic).** Tables du Tech Design §4 (users, budget_config, budget_ledger, wardrobe_items, captures, looks, look_pieces, matches, options, decisions, purchases).
  *AC :* `upgrade`/`downgrade` propres ; schéma conforme §4.
- **VS-03 · Identity stub (dev).** Utilisateur de dev + jeton simple ; scope `user_id` sur les requêtes.
  *AC :* toutes les routes sont scoptées à un user ; l'auth réelle est un epic ultérieur (noté).

## E1 — Wallet Engine  `↳ H1` *(accélérable via S&S Budget)*
**US :** en tant qu'utilisateur, je fixe un budget mensuel et je vois toujours mon solde réel.
- **VS-04 · Budget config + lecture wallet.** `POST /budget`, `GET /wallet`.
  *AC :* `available = base + Σ ROLLOVER_IN − Σ SPEND + Σ ADJUST` sur la période ; wallet jamais affiché négatif ; modif de base effective période suivante.
- **VS-05 · Ledger append-only.** Écritures immuables `SPEND|ADJUST|ROLLOVER_IN` ; **solde dérivé, jamais stocké**.
  *AC :* tests unitaires de dérivation sur combinaisons de types ; aucune colonne `remaining` mutable.
- **VS-06 · Job de report mensuel.** Tâche planifiée : `ROLLOVER_IN = min(available_fin_mois, cap)` (cap = 1× base), ouverture de période.
  *AC :* test de bascule de mois simulée ; plafond respecté ; idempotent sur re-run.

## E2 — Mock providers (ports & adapters)
**US :** en tant que dev, je veux le look et les options sans dépendre d'une API externe.
- **VS-07 · `DecompositionProvider` + Mock.** Interface + mock renvoyant le look v0.2 (style + 4 pièces). `POST /captures` (image factice) → look.
  *AC :* provider sélectionnable par config ; `GET /looks/{id}` renvoie style + pièces.
- **VS-08 · `ProductSearchProvider` + Mock.** Interface + mock renvoyant les 3 options fixes (39,99 / 49,99 [best] / 69,99) par gap.
  *AC :* `GET /gaps/{pieceId}/options` renvoie les options mockées + `purchase_score` (placeholder).

## E3 — Matching Engine  `↳ H3`
**US :** en tant qu'utilisateur, je vois ce que je possède déjà — et le système peut expliquer pourquoi.
- **VS-09 · Similarité attribut-based.** catégorie + couleur + coupe + matière → `owned_pct`, `is_owned`, flag anti-doublon (>80 %). J0 → 0 %.
  *AC :* penderie vide → 0 % (jamais de faux score) ; penderie amorcée → owned% corrects ; **chaque match porte une raison débogable** (attributs concordants).
- **VS-10 · Calcul des gaps.** `GET /looks/{id}/gaps` dérivé des matches.
  *AC :* `missing` = pièces du look non possédées.

## E4 — Decision Engine  `↳ H1, H2` *(le produit)*
**US :** en tant qu'utilisateur, je vois le solde après achat *avant* de décider, avec un verdict clair.
- **VS-11 · `POST /decisions/evaluate` (sans effet de bord).** Verdict `fits|tight|over` (`tight_threshold = max(15€, 15% × base)` depuis la config), `available_after`, `issues[]` (buy/phase/substitute/wait/recreate).
  *AC :* verdicts corrects aux bornes de prix ; **aucune écriture ledger** ; `available_after<0` → `over` avec montant en alerte.
- **VS-12 · PurchaseScore (stub) + badge « best ».** Classe les options (pondération placeholder), pose `is_best`.
  *AC :* `is_best` issu du score, **pas du prix seul**.
- **VS-13 · Stubs Phasing & Substitution.** `PhasingStrategy` → split illustratif (août/sept) ; `SubstitutionStrategy` → panier 92 €. Émettent `plan_created` / `substitution_selected`.
  *AC :* en `over`, étaler **et** substituer proposés **à parité** (pré-requis H2) ; algo stub, I/O figé.

## E5 — Confirmation & fermeture de boucle  `↳ H3`
**US :** quand je confirme un achat, ma penderie et mon budget se mettent à jour ensemble.
- **VS-14 · `POST /purchases/confirm` (transaction atomique).** Crée `purchase` + ligne `SPEND` + `wardrobe_item(owned)` en **une transaction**.
  *AC :* débit + ajout garde-robe atomiques ; `wallet.spent`/`available` à jour ; compteur penderie +1 ; garde d'idempotence.

## E6 — Analytics instrumentation  `↳ H1–H4`
**US :** en tant que Data PM, je veux mesurer l'activation et le compounding dès la bêta.
- **VS-15 · Emitter + schéma d'événements (PRD §7).** `budget_set`, `capture_started`, `look_decomposed`, `match_computed(owned_pct, capture_index k, regime)`, `gap_identified`, `options_viewed`, `option_selected`, `decision_viewed`, `decision_action_taken(action)`, `plan_created`, `substitution_selected`, `purchase_confirmed`, `wardrobe_item_added`, `return_session`.
  *AC :* **activation = `capture_started` → `decision_action_taken`** (l'`decision_viewed` seul ne compte pas) ; events validés contre un schéma typé ; sink dev = stdout, prod = SaaS.

## E7 — Client slice (Expo/RN)
**US :** je veux revivre la boucle v0.2 contre le vrai backend.
- **VS-16 · Onboarding + Wallet.** Fixer 100 € ; barre de solde persistante lisant `GET /wallet`.
- **VS-17 · Capture (déclencheur mock) → look → matching → gap → options** (depuis l'API).
- **VS-18 · Écran Décision.** Depuis `/decisions/evaluate` : solde après achat *avant* action + verdict + issues.
- **VS-19 · Confirmation.** `/purchases/confirm` → wallet + penderie à jour ; écran final (message de compounding).
- **VS-20 · Régimes J0 vs mature.** J0 penderie vide (0 %, chemin financier) ; mature amorcée ; émet `regime` + `capture_index`.

---

## Ordre de développement (atteindre l'E2E vite, puis élargir)

**Vague A — Walking skeleton** *(chemin heureux, verdict `fits`, mature amorcée, 1 option, confirmation)*
`VS-01 → VS-02 → VS-03 → VS-04 → VS-05 → VS-07 → VS-08 → VS-09 → VS-10 → VS-11 → VS-14 → VS-15 (events cœur) → VS-16 → VS-18 → VS-19`
➡️ **Jalon A :** set budget → capture mockée → décision réelle → confirmation → transaction Wallet+Wardrobe → événement d'activation. *Le moat tourne de bout en bout.*

**Vague B — Largeur**
`VS-06 (report) → VS-12 (score/badge) → VS-13 (stubs phasing/substitution + verdict over) → VS-17 (parcours complet) → VS-20 (J0/mature + regime/k) → VS-15 (events restants)`
➡️ **Jalon B :** les **deux régimes de v0.2** reproduits contre le backend, verdicts `fits/tight/over`, `match_computed` portant `k` (mesure H3).

*Rationale :* les engines (backend, sans dépendance externe) se construisent et se testent d'abord ; le client vient tout de suite après pour matérialiser l'E2E visible ; report et analytics s'intercalent.

## Definition of Done — du slice (critères de sortie)
- [ ] Les **deux régimes v0.2** (J0 + mature) sont reproductibles contre FastAPI + Postgres, providers mockés, événements émis.
- [ ] `decision_action_taken` déclenche l'activation, **vérifiable côté serveur** ; `decision_viewed` seul ne l'est pas.
- [ ] `/decisions/evaluate` prouvé **sans effet de bord** (test) ; seule `/purchases/confirm` mute.
- [ ] `docker compose up` depuis un checkout propre → parcours complet jouable.
- [ ] Remplacer un mock par un provider réel ne touche **aucun appelant** (test de swap sur `DecompositionProvider`).

## Après le slice
Remplacer les mocks (shortlist + benchmark vision / product-search), puis élargir aux epics restants (Identity réelle, Config/flags, EU/Vinted, reçus auto).

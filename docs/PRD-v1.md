# PRD V1 — Money layer for your wardrobe

> **Statut :** Draft · **Version :** 1.0 · **Date :** 18 août 2026
> **Chaîne amont :** competitive teardown → wedge → prototype v0.1 (baseline) → prototype v0.2 (comparatif J0/mature) → one-pager MVP → **ce PRD**
> **Principe directeur :** ce document est organisé par **hypothèses falsifiables (H1–H4)**, pas par liste de fonctionnalités. Chaque écran, règle ou événement existe pour tester une hypothèse et est mesuré.

---

## 1. Contexte & positionnement

**Positionnement.** Un *instrument financier pour s'habiller*, pas une app de mode avec un onglet budget. L'app relie **inspiration + garde-robe + budget** au moment précis de la décision d'achat.

**Hiérarchie produit (à ne jamais inverser) :**
- **Budget-first = moat.** Défendable, non copiable en un sprint. Gouverne le classement des options et la décision.
- **Capture-first = engagement.** Le déclencheur fréquent d'ouverture (inspiration sociale).
- **Recherche visuelle = commodité intégrée.** On ne construit pas son propre Lens ; on branche des sources existantes.

**Case blanche (scan août 2026).** Les apps de dressing regardent les dépenses *passées* (cost-per-wear) ; les apps de finances gèrent des enveloppes mais ignorent les vêtements. Aucune ne combine **enveloppe prospective + solde restant à la décision + report + intelligence garde-robe**.

## 2. Objectifs & non-objectifs

**Objectifs V1**
- Prouver que la boucle `capture → décision budgétaire` crée de la valeur dès la première session (y compris penderie vide).
- Instrumenter H1–H4 avec des signaux exploitables en bêta.
- Livrer un moteur de décision qui rend visible l'impact budgétaire *avant* l'achat.

**Non-objectifs V1 (explicitement hors scope)**
- Moteur de recherche visuelle propriétaire (intégration d'un fournisseur tiers uniquement).
- Checkout universel multi-marchands (on redirige vers le marchand).
- Feed social, essayage virtuel, styling pour le styling.
- Cost-per-wear comme fonction héroïque (au mieux secondaire).
- Parsing automatique des reçus/e-mails (cible V2 ; V1 = confirmation manuelle).

## 3. Colonne vertébrale — Hypothèses

| # | Hypothèse | Surfaces qui la testent | Signal mesurable | Seuil de rejet |
|---|-----------|------------------------|------------------|----------------|
| **H1** | Le budget seul produit assez de valeur dès **J0** (sans garde-robe). | Wallet, Capture, écran Décision J0 (plan / version qui rentre). | % de nouveaux atteignant une **1re décision budgétaire** ; complétion sans recourir au seeding de pièces. | < ~40 % de nouveaux atteignent une 1re décision → budget seul insuffisant comme accroche. |
| **H2** | En cas de dépassement, l'utilisateur a une **préférence exploitable** : étaler *ou* substituer. | Écran Décision (états `over`), toggle plan/substitution. | Répartition des choix étaler / version qui rentre / attendre ; taux de bascule entre vues. | Aucune option > ~15–20 % (indécision) → l'écran ne guide pas. |
| **H3** | L'**accumulation de garde-robe** augmente la valeur perçue au point de faire revenir. | Matching, fermeture de boucle, capture k. | % de matching à la capture *k* (croissance) ; retour J+14/J+30 après 1re décision. | Matching ne croît pas avec *k*, ou pas d'effet sur le retour → compounding ≠ moteur de rétention. |
| **H4** | Le segment « acheter mieux » **paie un abonnement** (l'affiliation entre en conflit avec le discours anti-surconsommation). | Paywall (tiers avancé), attribution seconde-main. | Intention/conversion vers tier payant ; sensibilité à l'affiliation Vinted uniquement. | Conversion trop faible *et* rejet affiliation → revoir le modèle. |

> **Règle de rédaction du reste du PRD :** chaque section fonctionnelle indique `↳ teste : Hx`.

## 4. Régimes utilisateur (états précis)

Deux régimes du **même** produit, pilotés par l'état de la garde-robe. Le sélecteur du prototype v0.2 les simule ; en production, ils sont continus.

### 4.1 J0 — zéro-data  `↳ teste : H1`
- **État initial :** garde-robe = 0 pièce ; budget de base défini à l'onboarding ; dépensé = 0.
- **Matching :** impossible → l'écran l'assume (« 0 %, on raisonne d'abord budget ») ; n'affiche jamais un faux pourcentage.
- **Wow attendu :** *financier*. Reproduire le look de zéro coûte > enveloppe → **plan multi-mois** ou **version qui rentre**.
- **Seeding optionnel :** « ajouter mes N pièces les plus portées » = **skippable**, jamais un gate. S'il est utilisé, le matching se recalcule immédiatement.

### 4.2 Mature  `↳ teste : H3`
- **État :** garde-robe peuplée (≥ ~15 pièces couvrant hauts/bas/veste/chaussures) ; historique de dépenses.
- **Matching :** actif (« tu possèdes déjà X % »).
- **Wow attendu :** *vestimentaire*. Le manque est réduit à 1–2 pièces ; la décision porte sur le complément.

### 4.3 Transition (compounding)  `↳ teste : H3`
Chaque achat confirmé fait passer une pièce de *manquante* à *possédée* et met le budget à jour. La valeur perçue doit migrer du financier (J0) au vestimentaire (mature). **À instrumenter** : taux de matching par capture successive.

## 5. Modèle de domaine (minimal)

- **BudgetEnvelope** : `base_amount`, `period` (mois calendaire V1), `spent`, `rollover_in`, `available = base + rollover_in − spent`, `rollover_cap`.
- **WardrobeItem** : `id`, `category`, `attributs` (couleur, coupe, matière), `price?`, `source` (photo / reçu / achat in-app), `acquired_at`, `owned=true`.
- **Look/Capture** : `id`, `source` (screenshot/share), `style`, `pieces[]` (catégorie + attributs + swatch).
- **Gap** : pièces du look non couvertes par la garde-robe.
- **Option** : candidat achetable pour combler un gap (`price`, `merchant`, `purchase_score`).
- **Decision** : `verdict` (`fits`/`tight`/`over`), `issue` prise, `montant`, horodatage.

## 6. Spécifications fonctionnelles

### 6.1 Onboarding & Wallet  `↳ teste : H1, H4`

**Règles du wallet (décision V1 ; variantes en §9) :**
1. L'utilisateur fixe un **budget de base mensuel** (ex. 100 €), modifiable à tout moment (prend effet à la période suivante).
2. L'enveloppe **se réinitialise le 1er du mois** à `base_amount`.
3. Le **solde non dépensé se reporte** sur le mois suivant (`rollover_in`), **plafonné à 1× la base** (`available` max = 2× base). Plafond configurable.
4. Tout achat confirmé **décrémente `available`** (base puis rollover).
5. « Attendre l'enveloppe de septembre » = **différer l'intention** vers la période suivante (crée un rappel, ne dépense rien).
6. Ajustement manuel du dépensé autorisé (corrections).

**Critères d'acceptation**
- [ ] `available` = `base + rollover_in − spent` à tout instant, jamais négatif à l'affichage du wallet.
- [ ] Au passage de mois, `rollover_in` = min(`available` fin de mois, `rollover_cap`) ; `spent` remis à 0.
- [ ] Modifier la base n'altère pas la période en cours.
- [ ] Le solde restant est **visible en permanence** (barre persistante) sur tous les écrans du parcours.

### 6.2 Capture & décomposition  `↳ commodité`
- Entrées : capture d'écran importée **ou** partage (share-sheet) depuis une app tierce **ou** photo.
- Sortie : `style` détecté + `pieces[]` (catégorie, attributs, swatch), via **fournisseur tiers** de vision/produits.
- **Critères d'acceptation**
  - [ ] Une capture produit ≥ 1 pièce détectée ou un état d'erreur explicite (« look non reconnu, réessaie »).
  - [ ] Le nom du fournisseur/coût n'est jamais exposé comme valeur produit.

### 6.3 Garde-robe & matching  `↳ teste : H3`
- Matching : pour chaque pièce du look, similarité avec les items possédés → `owned%` ou `manquant`.
- Score de look = `pièces possédées / pièces du look`.
- **États vides** = invitation à agir (pas un mur) ; seeding skippable (§4.1).
- Ajout de pièces : photo, description fabricant, ou **automatique après achat confirmé** (§6.5).
- **Critères d'acceptation**
  - [ ] Penderie vide → 0 % assumé, aucun faux pourcentage.
  - [ ] Ajouter des pièces recalcule le matching **immédiatement** sur le look courant.
  - [ ] Un achat confirmé crée un `WardrobeItem` `owned=true` et incrémente le compteur.

### 6.4 Moteur de décision (le produit)  `↳ teste : H1, H2`

**6.4.1 Verdict (règles, configurables)**
```
available_after = available − price
tight_threshold = max(15 €, 15% × base_amount)
verdict = over   si available_after < 0
        = tight  si 0 ≤ available_after < tight_threshold
        = fits   sinon
```
- **Contrat UI :** le **solde après achat** est affiché *avant* l'action, avec le verdict en un mot (`Ça passe` / `Juste, mais ça passe` / `Ça déborde`).

**6.4.2 Issues proposées**
- `fits` / `tight` → **Acheter**, + alternatives (moins cher, attendre, recréer sans acheter).
- `over` → **deux remèdes**, présentés à parité pour tester H2 :
  - **Étaler** (plan multi-enveloppes) — *interface définie, algorithme hors-scope V1* (§9-1).
  - **Substituer** (« version qui rentre » ≤ available) — *interface définie, logique hors-scope V1* (§9-2).
  - + Attendre l'enveloppe suivante / Recréer avec la garde-robe seule.

**6.4.3 Classement des options — Purchase Score (ranking, pas gate)**
```
PurchaseScore = f(style_match, wardrobe_complementarity, outfit_potential,
                  budget_fit, price_value, user_preference)
```
- V1 : entrées définies ; **pondération TBD** ; usage = trier les options et attribuer le badge « meilleure pour ta penderie ».
- **Anti-doublon :** signaler si similarité à un item possédé > seuil (défaut 80 %).

**Critères d'acceptation**
- [ ] `available_after` et le verdict sont exacts pour tout `price` (dont `over` → montant négatif affiché en alerte).
- [ ] En `over`, étaler **et** substituer sont proposés avec la même proéminence (pré-requis H2).
- [ ] Le badge « meilleure pour ta penderie » découle du PurchaseScore, pas du prix seul.
- [ ] Aucune issue n'est un cul-de-sac : chaque bouton mène à un état défini.

### 6.5 Confirmation & fermeture de boucle  `↳ teste : H3`
- Après redirection marchand : prompt **« Tu l'as acheté ? »** (Oui / Pas encore).
- Oui → `WardrobeItem` créé (`owned=true`) **et** `spent += price` (mise à jour simultanée).
- **Critères d'acceptation**
  - [ ] « Oui » met à jour budget **et** garde-robe dans la même transaction.
  - [ ] « Pas encore » ne modifie ni budget ni garde-robe ; peut créer un item de wishlist.
  - [ ] L'écran final annonce le compounding (« ta prochaine capture saura déjà ce que tu possèdes »).

## 7. Analytics — événements & funnel  `↳ instrumente H1–H4`

**Funnel d'activation :** `capture_started → look_decomposed → (match_computed) → decision_viewed → decision_action_taken`

| Événement | Propriétés clés | Hypothèse |
|-----------|-----------------|-----------|
| `budget_set` | base_amount, rollover_cap | H1, H4 |
| `capture_started` | source (screenshot/share/photo) | H1 |
| `look_decomposed` | pieces_count, style | H1 |
| `match_computed` | owned_pct, capture_index *k*, regime (j0/mature) | **H3** |
| `gap_identified` | missing_count | H1 |
| `options_viewed` | options_count | H2 |
| `option_selected` | price, purchase_score, is_best | H2 |
| `decision_viewed` | verdict (fits/tight/over), available, price | H1, H2 |
| `decision_action_taken` | action (buy/phase/substitute/wait/recreate) | **H1, H2** |
| `plan_created` / `plan_started` | months_count, month1_total | H2 |
| `substitution_selected` | bundle_price, delta_vs_original | H2 |
| `purchase_confirmed` | price, pieces_added | H3 |
| `wardrobe_item_added` | source (photo/receipt/purchase), category | H3 |
| `return_session` | days_since_first_decision | **H3** |
| `paywall_viewed` / `subscription_started` | tier | **H4** |

**Définitions de mesure**
- **Activation** = `capture_started` suivi de `decision_action_taken` (même utilisateur). **Une action réelle est requise — l'affichage seul de l'écran (`decision_viewed`) ne compte pas.**
- **Variante J0** = `capture_started → (plan_started | substitution_selected | decision_action_taken)`.
- **North-star candidate** = captures-avec-décision par utilisateur actif / mois.
- **Rétention (H3)** = % `return_session` à J+14 après la 1re décision ; corrélé à `owned_pct` croissant.

## 8. Critères d'acceptation transverses (quality floor)
- [ ] Solde restant visible sur **tous** les écrans du parcours.
- [ ] Parcours complet possible en **J0** (penderie vide) sans blocage.
- [ ] Parcours complet possible en **mature** (matching actif).
- [ ] Aucun événement analytics manquant sur le funnel d'activation.
- [ ] États vides et erreurs = messages orientés action (voix de l'interface, pas d'excuse).
- [ ] Accessibilité : focus clavier visible, contrastes suffisants, `prefers-reduced-motion` respecté.

## 9. Décisions produit ouvertes (à trancher — conservées comme inconnues structurantes)
1. **Moteur de phasing** — quelles pièces d'abord (ancrage stylistique ? valeur marginale ? prix ?). *V1 : interface + split illustratif ; algo hors-scope, instrumenté via H2.*
2. **Logique de substitution** — équivalence de style sous contrainte budgétaire. *V1 : interface + panier fictif ; logique hors-scope, instrumentée via H2.*
3. **Wallet** — mois calendaire vs fenêtre glissante 30 j ; plafond de report ; sous-enveloppes (vêtements/chaussures/accessoires) → V2.
4. **Modèle éco (H4)** — abonnement vs freemium ; affiliation limitée au seconde-main (Vinted) ; angle EU-native.
5. **Cold-start** — UX de seeding et déclencheurs d'ajout automatique (reçus) → V2.

## 10. Hors scope V1 → pistes V2+
Parsing auto reçus/e-mails · routage « pièce manquante » vers Vinted (EU-native) · sous-enveloppes budgétaires · essayage virtuel · social · cost-per-wear avancé · checkout intégré.

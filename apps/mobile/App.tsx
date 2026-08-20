import {useMemo, useState} from "react";
import {
  ActivityIndicator,
  Linking,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import {api, Evaluation, Look, Option, Wallet} from "./src/api";

type Step = "onboarding" | "wallet" | "look" | "options" | "decision" | "confirmed";

const money = (value: number) => `${value.toFixed(2).replace(".", ",")} €`;

export default function App() {
  const [baseUrl, setBaseUrl] = useState(process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000");
  const [budgetInput, setBudgetInput] = useState("100");
  const [step, setStep] = useState<Step>("onboarding");
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [look, setLook] = useState<Look | null>(null);
  const [missing, setMissing] = useState<string[]>([]);
  const [options, setOptions] = useState<Option[]>([]);
  const [selected, setSelected] = useState<Option | null>(null);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ownedCount = useMemo(() => look?.pieces.filter((piece) => piece.is_owned).length ?? 0, [look]);

  async function run<T>(fn: () => Promise<T>): Promise<T | null> {
    setBusy(true);
    setError(null);
    try {
      return await fn();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Erreur inconnue");
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function start() {
    const amount = Number(budgetInput.replace(",", "."));
    if (!Number.isFinite(amount) || amount <= 0) {
      setError("Entre un budget supérieur à 0 €.");
      return;
    }
    const nextWallet = await run(() => api.setBudget(baseUrl, amount));
    if (!nextWallet) return;
    setWallet(nextWallet);
    setStep("wallet");
  }

  async function capture() {
    const result = await run(async () => {
      const created = await api.createCapture(baseUrl);
      const nextLook = await api.look(baseUrl, created.look_id);
      const gaps = await api.gaps(baseUrl, created.look_id);
      return {nextLook, gaps};
    });
    if (!result) return;
    setLook(result.nextLook);
    setMissing(result.gaps.missing);
    setStep("look");
  }

  async function loadOptions() {
    const pieceId = missing[0];
    if (!pieceId) return;
    const result = await run(() => api.options(baseUrl, pieceId));
    if (!result) return;
    setOptions(result.options);
    setSelected(result.options.find((option) => option.is_best) ?? result.options[0] ?? null);
    setStep("options");
  }

  async function decide(option: Option) {
    const result = await run(() => api.evaluate(baseUrl, option.id));
    if (!result) return;
    setSelected(option);
    setEvaluation(result);
    setStep("decision");
  }

  async function act(action: string) {
    if (!selected) return;
    const result = await run(() => api.takeAction(baseUrl, selected.id, action));
    if (!result) return;
    if (action === "buy" && selected.affiliate_url) {
      await Linking.openURL(selected.affiliate_url).catch(() => undefined);
    }
  }

  async function confirm() {
    if (!selected) return;
    const key = `mobile-${selected.id}-${Date.now()}`;
    const result = await run(() => api.confirmPurchase(baseUrl, selected.id, key));
    if (!result) return;
    setWallet(result.wallet);
    setStep("confirmed");
  }

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.page} keyboardShouldPersistTaps="handled">
        <View style={styles.brandRow}>
          <Text style={styles.brand}>FASHION MONEY</Text>
          <Text style={styles.kicker}>budget-first · capture-first</Text>
        </View>

        {step === "onboarding" && (
          <Card>
            <Text style={styles.eyebrow}>01 · TON ENVELOPPE</Text>
            <Text style={styles.title}>Combien veux-tu consacrer aux vêtements ce mois-ci ?</Text>
            <Text style={styles.copy}>Le budget est la seule donnée obligatoire. La penderie peut rester vide à J0.</Text>
            <TextInput
              accessibilityLabel="Budget mensuel"
              keyboardType="decimal-pad"
              value={budgetInput}
              onChangeText={setBudgetInput}
              style={styles.moneyInput}
            />
            <Text style={styles.label}>API backend</Text>
            <TextInput
              autoCapitalize="none"
              autoCorrect={false}
              value={baseUrl}
              onChangeText={setBaseUrl}
              style={styles.input}
            />
            <PrimaryButton label="Créer mon enveloppe" onPress={start} />
          </Card>
        )}

        {step === "wallet" && wallet && (
          <>
            <WalletCard wallet={wallet} />
            <Card>
              <Text style={styles.eyebrow}>02 · INSPIRATION</Text>
              <Text style={styles.title}>Un look t’a tapé dans l’œil ?</Text>
              <Text style={styles.copy}>Pour ce slice, la capture est mockée côté backend. Le flux produit est réel.</Text>
              <PrimaryButton label="Analyser une capture" onPress={capture} />
            </Card>
          </>
        )}

        {step === "look" && look && (
          <Card>
            <Text style={styles.eyebrow}>03 · CE QUE TU AS DÉJÀ</Text>
            <Text style={styles.bigNumber}>{look.score_look}%</Text>
            <Text style={styles.title}>{look.style ?? "Style détecté"}</Text>
            <Text style={styles.copy}>
              {ownedCount === 0
                ? "Penderie vide : on raisonne d’abord budget."
                : `${ownedCount} pièce(s) sur ${look.pieces.length} déjà couvertes.`}
            </Text>
            {look.pieces.map((piece) => (
              <View key={piece.id} style={styles.row}>
                <Text style={styles.rowTitle}>{piece.category}</Text>
                <Text style={piece.is_owned ? styles.good : styles.muted}>
                  {piece.is_owned ? "déjà possédé" : "manquant"}
                </Text>
              </View>
            ))}
            <PrimaryButton
              label={missing.length ? `Voir ${missing.length} pièce(s) à compléter` : "Tout est déjà couvert"}
              onPress={loadOptions}
              disabled={!missing.length}
            />
          </Card>
        )}

        {step === "options" && (
          <Card>
            <Text style={styles.eyebrow}>04 · OPTIONS</Text>
            <Text style={styles.title}>Trois choix. Pas quarante-huit.</Text>
            <Text style={styles.copy}>Le meilleur choix est classé par PurchaseScore côté backend.</Text>
            {options.map((option) => (
              <Pressable key={option.id} style={[styles.option, option.is_best && styles.optionBest]} onPress={() => decide(option)}>
                <View>
                  <Text style={styles.rowTitle}>{option.merchant ?? "Marchand"}</Text>
                  <Text style={styles.muted}>Similarité {option.similarity ?? "—"}%</Text>
                </View>
                <View style={styles.right}>
                  <Text style={styles.optionPrice}>{money(option.price)}</Text>
                  {option.is_best && <Text style={styles.best}>MEILLEUR CHOIX</Text>}
                </View>
              </Pressable>
            ))}
          </Card>
        )}

        {step === "decision" && evaluation && selected && (
          <>
            <WalletCard wallet={wallet ?? {period: "", base: 0, rollover_in: 0, spent: 0, available: evaluation.available}} />
            <Card>
              <Text style={styles.eyebrow}>05 · DÉCISION</Text>
              <Text style={styles.title}>Ton solde après achat</Text>
              <View style={styles.balanceFlow}>
                <Text style={styles.balanceBefore}>{money(evaluation.available)}</Text>
                <Text style={styles.arrow}>→</Text>
                <Text style={styles.balanceAfter}>{money(evaluation.available_after)}</Text>
              </View>
              <Verdict verdict={evaluation.verdict} />
              <Text style={styles.copy}>Prix de la pièce : {money(evaluation.price)}. Le solde est montré avant que tu décides.</Text>
              {evaluation.verdict !== "over" ? (
                <>
                  <PrimaryButton label={`Continuer vers l'achat · ${money(selected.price)}`} onPress={() => act("buy")} />
                  <SecondaryButton label="J'ai acheté cette pièce" onPress={confirm} />
                </>
              ) : (
                <>
                  <PrimaryButton label="Étaler sur 2 mois" onPress={() => act("phase")} />
                  <SecondaryButton label="Trouver une substitution" onPress={() => act("substitute")} />
                  <SecondaryButton label="Attendre" onPress={() => act("wait")} />
                </>
              )}
            </Card>
          </>
        )}

        {step === "confirmed" && wallet && (
          <>
            <WalletCard wallet={wallet} />
            <Card>
              <Text style={styles.eyebrow}>06 · BOUCLE REFERMÉE</Text>
              <Text style={styles.title}>Budget débité. Penderie enrichie.</Text>
              <Text style={styles.copy}>Ta prochaine capture saura déjà que cette pièce existe. Le produit commence à composer sa valeur dans le temps.</Text>
              <PrimaryButton label="Faire une nouvelle capture" onPress={capture} />
            </Card>
          </>
        )}

        {busy && <ActivityIndicator size="large" />}
        {error && <Text style={styles.error}>{error}</Text>}
      </ScrollView>
    </SafeAreaView>
  );
}

function Card({children}: {children: React.ReactNode}) {
  return <View style={styles.card}>{children}</View>;
}

function WalletCard({wallet}: {wallet: Wallet}) {
  return (
    <Card>
      <Text style={styles.eyebrow}>WALLET · {wallet.period || "MOIS EN COURS"}</Text>
      <Text style={styles.walletAmount}>{money(wallet.available)}</Text>
      <Text style={styles.muted}>restants sur {money(wallet.base)} · dépensé {money(wallet.spent)}</Text>
      <View style={styles.track}>
        <View style={[styles.fill, {width: `${Math.max(0, Math.min(100, wallet.base ? (wallet.available / wallet.base) * 100 : 0))}%`}]} />
      </View>
    </Card>
  );
}

function Verdict({verdict}: {verdict: Evaluation["verdict"]}) {
  const label = verdict === "fits" ? "ÇA PASSE" : verdict === "tight" ? "JUSTE, MAIS ÇA PASSE" : "ÇA DÉBORDE";
  return <Text style={[styles.verdict, verdict === "over" && styles.verdictOver]}>{label}</Text>;
}

function PrimaryButton({label, onPress, disabled = false}: {label: string; onPress: () => void; disabled?: boolean}) {
  return (
    <Pressable disabled={disabled} onPress={onPress} style={[styles.primary, disabled && styles.disabled]}>
      <Text style={styles.primaryText}>{label}</Text>
    </Pressable>
  );
}

function SecondaryButton({label, onPress}: {label: string; onPress: () => void}) {
  return (
    <Pressable onPress={onPress} style={styles.secondary}>
      <Text style={styles.secondaryText}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  safe: {flex: 1, backgroundColor: "#F3F1EB"},
  page: {padding: 20, gap: 16, paddingBottom: 48},
  brandRow: {paddingTop: 8, paddingBottom: 4},
  brand: {fontSize: 22, fontWeight: "900", letterSpacing: 1.4, color: "#161616"},
  kicker: {fontSize: 12, color: "#6E6A63", marginTop: 4},
  card: {backgroundColor: "#FFFFFF", borderRadius: 24, padding: 20, gap: 14, borderWidth: 1, borderColor: "#E7E3DB"},
  eyebrow: {fontSize: 11, fontWeight: "800", letterSpacing: 1.3, color: "#7A746B"},
  title: {fontSize: 26, lineHeight: 31, fontWeight: "800", color: "#171717"},
  copy: {fontSize: 15, lineHeight: 22, color: "#5F5A53"},
  label: {fontSize: 12, fontWeight: "700", color: "#777168", marginTop: 4},
  input: {borderWidth: 1, borderColor: "#D8D2C8", borderRadius: 14, padding: 14, color: "#171717"},
  moneyInput: {fontSize: 48, fontWeight: "800", color: "#171717", borderBottomWidth: 1, borderColor: "#D8D2C8", paddingVertical: 8},
  primary: {backgroundColor: "#171717", borderRadius: 16, paddingVertical: 16, paddingHorizontal: 18, alignItems: "center", marginTop: 4},
  primaryText: {color: "#FFFFFF", fontSize: 15, fontWeight: "800"},
  secondary: {borderWidth: 1, borderColor: "#BBB4A9", borderRadius: 16, paddingVertical: 15, paddingHorizontal: 18, alignItems: "center"},
  secondaryText: {color: "#171717", fontSize: 15, fontWeight: "700"},
  disabled: {opacity: 0.4},
  error: {backgroundColor: "#FFE4E0", color: "#8A241C", padding: 14, borderRadius: 14},
  walletAmount: {fontSize: 46, fontWeight: "900", color: "#171717", fontVariant: ["tabular-nums"]},
  bigNumber: {fontSize: 56, fontWeight: "900", color: "#171717", fontVariant: ["tabular-nums"]},
  muted: {fontSize: 13, color: "#7B756D"},
  good: {fontSize: 13, color: "#2F6B47", fontWeight: "700"},
  track: {height: 8, backgroundColor: "#ECE8E0", borderRadius: 99, overflow: "hidden"},
  fill: {height: 8, backgroundColor: "#171717", borderRadius: 99},
  row: {flexDirection: "row", justifyContent: "space-between", gap: 12, paddingVertical: 10, borderBottomWidth: StyleSheet.hairlineWidth, borderColor: "#DED9D0"},
  rowTitle: {fontSize: 15, fontWeight: "700", color: "#171717", textTransform: "capitalize"},
  option: {flexDirection: "row", justifyContent: "space-between", alignItems: "center", padding: 16, borderWidth: 1, borderColor: "#DED9D0", borderRadius: 16},
  optionBest: {borderWidth: 2, borderColor: "#171717"},
  right: {alignItems: "flex-end"},
  optionPrice: {fontSize: 21, fontWeight: "800", fontVariant: ["tabular-nums"]},
  best: {fontSize: 9, fontWeight: "900", letterSpacing: 0.8, marginTop: 3},
  balanceFlow: {flexDirection: "row", alignItems: "center", justifyContent: "space-between"},
  balanceBefore: {fontSize: 28, fontWeight: "700", color: "#817B73", fontVariant: ["tabular-nums"]},
  arrow: {fontSize: 24, color: "#9A948C"},
  balanceAfter: {fontSize: 36, fontWeight: "900", color: "#171717", fontVariant: ["tabular-nums"]},
  verdict: {alignSelf: "flex-start", paddingHorizontal: 12, paddingVertical: 7, borderRadius: 999, backgroundColor: "#DDEFE3", color: "#205B36", fontSize: 11, fontWeight: "900", letterSpacing: 0.7},
  verdictOver: {backgroundColor: "#FFE3DE", color: "#8A241C"},
});

# Mobile (Expo / React Native)

Client for the vertical slice (VS-16..VS-20). Wires to the backend API:
onboarding + wallet, capture (mock trigger), look/match/gap/options,
decision (from `/decisions/evaluate`), confirmation (`/purchases/confirm`).

No financial/business rule lives here — balance, verdict and rollover come
from the backend. To scaffold: `npx create-expo-app@latest`.

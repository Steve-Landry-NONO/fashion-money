# Fashion Money Mobile

Expo / React Native client for the Vertical Slice 1 moat flow.

The client intentionally keeps business rules out of the UI. Wallet balances, matching, verdicts and purchase mutations all come from FastAPI.

## Flow

`budget → wallet → mock capture → look/matching → gaps → options → decision → action → purchase confirmation → updated wallet`

The first slice uses the backend's deterministic mock decomposition and product-search providers. Real camera/share-sheet ingestion is a later provider/UI integration.

## Run

```bash
cd apps/mobile
npm install
npm run typecheck
npm start
```

The app defaults to `http://localhost:8000`. On a physical phone, set the API field on the onboarding screen to your computer's LAN address, for example `http://192.168.1.25:8000`, or set `EXPO_PUBLIC_API_URL` before starting Expo.

Use the backend dev token path; authentication hardening is out of scope for this slice.

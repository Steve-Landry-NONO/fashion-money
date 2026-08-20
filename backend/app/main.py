from fastapi import FastAPI

from app import db  # noqa: F401
from app.capture import models as _capture  # noqa: F401
from app.capture.router import router as capture_router
from app.catalog import models as _catalog  # noqa: F401
from app.catalog.router import router as catalog_router
from app.decision import models as _decision  # noqa: F401
from app.decision.router import router as decision_router
from app.identity import models as _identity  # noqa: F401
from app.matching import models as _matching  # noqa: F401
from app.matching.router import router as matching_router
from app.wallet import models as _wallet  # noqa: F401
from app.wallet.router import router as wallet_router

app = FastAPI(title="Fashion Money API", version="0.2.0")
app.include_router(wallet_router)
app.include_router(capture_router)
app.include_router(matching_router)
app.include_router(catalog_router)
app.include_router(decision_router)


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok"}

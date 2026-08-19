from fastapi import FastAPI

# import models so metadata is populated (Alembic target + tests create_all)
from app import db  # noqa: F401
from app.capture import models as _capture  # noqa: F401
from app.catalog import models as _catalog  # noqa: F401
from app.decision import models as _decision  # noqa: F401
from app.identity import models as _identity  # noqa: F401
from app.matching import models as _matching  # noqa: F401
from app.wallet import models as _wallet  # noqa: F401
from app.wallet.router import router as wallet_router

app = FastAPI(title="Fashion Money API", version="0.1.0")
app.include_router(wallet_router)


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok"}

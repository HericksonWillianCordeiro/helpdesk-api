from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes.audit import router as audit_router
from app.api.routes.auth import router as auth_router
from app.api.routes.categories import router as categories_router
from app.api.routes.comments import router as comments_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.sla import router as sla_router
from app.api.routes.tickets import router as tickets_router
from app.api.routes.users import router as users_router
from app.core.config import settings
from app.core.database import get_db

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API REST para gerenciamento de chamados de suporte de TI.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(audit_router)
app.include_router(categories_router)
app.include_router(tickets_router)
app.include_router(comments_router)
app.include_router(users_router)
app.include_router(notifications_router)
app.include_router(sla_router)
app.include_router(dashboard_router)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["Health"])
def readiness_check(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Banco de dados indisponível",
        ) from None
    return {"status": "ready"}

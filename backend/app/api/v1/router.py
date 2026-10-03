from fastapi import APIRouter

from app.api.v1.routes import files

router = APIRouter()
router.include_router(files.router, prefix="/files", tags=["files"])

from fastapi import APIRouter

from app.api.v1.routes import exports, files

router = APIRouter()
router.include_router(files.router, prefix="/files", tags=["files"])
router.include_router(exports.router, prefix="/export", tags=["export"])

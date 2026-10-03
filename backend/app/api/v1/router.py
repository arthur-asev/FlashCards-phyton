from fastapi import APIRouter

from app.api.v1.routes import ai, cards, decks, exports, files, jobs, reviews, taxonomy

router = APIRouter()
router.include_router(files.router, prefix="/files", tags=["files"])
router.include_router(exports.router, prefix="/export", tags=["export"])
router.include_router(decks.router, prefix="/decks", tags=["decks"])
router.include_router(cards.router, prefix="/cards", tags=["cards"])
router.include_router(taxonomy.router, tags=["taxonomy"])
router.include_router(ai.router, prefix="/ai", tags=["ai"])
router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
router.include_router(reviews.router, tags=["reviews"])

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.services.attraction import AttractionService

router = APIRouter(prefix="/api/v1/attraction", tags=["attraction"])
attraction_service = AttractionService()


@router.get("/search")
async def search_attractions(query: str) -> Dict[str, Any]:
    """
    어트랙션 검색 엔드포인트
    """
    try:
        result = await attraction_service.search_attractions(query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

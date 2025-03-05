from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.services.restaurant import RestaurantService

router = APIRouter(prefix="/api/v1/restaurants", tags=["restaurants"])
restaurant_service = RestaurantService()


@router.get("/search")
async def search_restaurants(query: str) -> Dict[str, Any]:
    """
    레스토랑 검색 엔드포인트
    """
    try:
        result = await restaurant_service.search_restaurants(query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

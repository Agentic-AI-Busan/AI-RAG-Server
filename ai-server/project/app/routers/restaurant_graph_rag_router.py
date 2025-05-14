from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Any, Dict, Annotated, Union
from datetime import datetime, date

from app.services.restaurant_graph_rag_service import RestaurantGraphRAGService
from app.services.restaurant import RestaurantResponse

# 기존 restaurant.py 라우터에서 RestaurantSearchRequest 가져오기
from app.routers.restaurant import RestaurantSearchRequest

router = APIRouter(
    prefix="/api/v1/restaurant_graph_rag",
    tags=["restaurant_graph_rag"]
)

restaurant_service = RestaurantGraphRAGService()

@router.post("/search", response_model=RestaurantResponse)
async def search_restaurants_with_graph_rag(
    request: RestaurantSearchRequest
) -> Dict[str, Any]:
    """
    그래프 RAG를 활용하여 사용자 쿼리에 맞는 레스토랑을 검색하고 추천합니다.
    (입력 및 출력 스키마는 기존 /api/v1/restaurants/search 와 동일)
    """
    try:
        query_to_search = request.create_query()
        if not query_to_search:
            raise HTTPException(status_code=400, detail="검색 쿼리를 생성할 수 없습니다. 입력값을 확인해주세요.")
            
        result = await restaurant_service.search_restaurants_with_graph_rag(query_to_search)
        return result
    except Exception as e:
        print(f"Restaurant Graph RAG search_restaurants API 오류: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"레스토랑 검색 중 오류 발생: {str(e)}")

# 다른 엔드포인트가 필요하다면 여기에 추가 (예: 상세 정보 조회 등) 
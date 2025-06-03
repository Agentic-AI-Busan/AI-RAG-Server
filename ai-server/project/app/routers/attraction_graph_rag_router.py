from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Union # Union 추가
from datetime import datetime, date # datetime, date 추가

# 새로운 Graph RAG 서비스 import
from app.services.attraction_graph_rag_service import AttractionGraphRAGService
# 기존 Attraction 서비스에서 응답 스키마 및 요청 스키마에 필요한 Pydantic 모델 가져오기
from app.services.attraction import AttractionResponse # Recommendation은 AttractionResponse 내부에서 사용됨
from app.routers.attraction import AttractionSearchRequest # 기존 라우터에서 요청 스키마 가져오기

# pydantic validator는 AttractionSearchRequest 내부에 있으므로 별도 import 불필요

router = APIRouter(
    prefix="/api/v1/attraction_graph_rag",
    tags=["attraction_graph_rag"]
)

attraction_service = AttractionGraphRAGService()

@router.post("/search", response_model=AttractionResponse)
async def search_attractions_with_graph_rag(
    request: AttractionSearchRequest
) -> Dict[str, Any]:
    """
    그래프 RAG를 활용하여 사용자 쿼리에 맞는 관광지를 검색하고 추천합니다.
    (입력 및 출력 스키마는 기존 /api/v1/attraction/search 와 동일)
    """
    try:
        query_to_search = request.create_query()
        if not query_to_search:
            raise HTTPException(status_code=400, detail="검색 쿼리를 생성할 수 없습니다. 입력값을 확인해주세요.")

        result = await attraction_service.search_attractions_with_graph_rag(query_to_search)
        return result
    except Exception as e:
        print(f"Attraction Graph RAG search_attractions API 오류: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"관광지 검색 중 오류 발생: {str(e)}") 
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Tuple

from ..services.query_router import QueryRouterService

router = APIRouter()

def get_query_router_service() -> QueryRouterService:
    """의존성 주입을 위한 QueryRouterService 인스턴스 생성 함수"""
    try:
        # 필요시 여기에 서비스 생성 관련 로직 추가 가능
        service_instance = QueryRouterService()
        print("QueryRouterService 인스턴스 생성") # 생성 시점 확인용 로그
        return service_instance
    except Exception as e:
        print(f"오류: QueryRouterService 인스턴스 생성 실패 - {e}")
        # 서비스 생성 실패 시 503 Service Unavailable 오류 발생
        raise HTTPException(status_code=503, detail="Query Router Service unavailable")

# 요청 본문 모델 정의 (POST 방식 사용 시)
class RouteRequest(BaseModel):
    query: str = Field(..., description="사용자 질문")
    chat_history: List[Tuple[str, str]] = Field(default=[], description="대화 기록 ([(사용자 질문, AI 답변), ...])")

# 응답 모델 정의
class RouteResponse(BaseModel):
    query: str
    category: str
    chat_history_length: int

@router.post("/route-test", response_model=RouteResponse)
async def test_routing_post(
    request: RouteRequest,
    service: QueryRouterService = Depends(get_query_router_service) # 서비스 주입
):
    """
    POST 방식으로 사용자 쿼리와 대화 기록을 받아 라우팅 결과를 반환하는 테스트 엔드포인트.
    """
    print(f"API 요청 수신 (POST /route-test): query='{request.query}', history_len={len(request.chat_history)}")
    # 주입된 service 객체 사용
    category = await service.route(query=request.query, chat_history=request.chat_history)
    return RouteResponse(
        query=request.query, 
        category=category, 
        chat_history_length=len(request.chat_history)
    )
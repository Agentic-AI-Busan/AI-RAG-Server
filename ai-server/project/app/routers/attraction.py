from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.services.attraction import AttractionService, AttractionResponse
from pydantic import BaseModel, validator
from datetime import datetime, date
from typing import Union

router = APIRouter(prefix="/api/v1/attraction", tags=["attraction"])
attraction_service = AttractionService()

# POST 요청을 위한 요청 모델 정의
class AttractionSearchRequest(BaseModel):
    city: str
    startDate: date  # 날짜 형식으로 자동 변환
    endDate: date    # 날짜 형식으로 자동 변환
    preferActivity: Union[str, None] = None  # 문자열 또는 null 값 허용
    requirement: Union[str, None] = None     # 문자열 또는 null 값 허용
    
    @validator('startDate', 'endDate', pre=True)
    def parse_date(cls, value):
        """문자열을 date 객체로 변환"""
        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError(f"Invalid date format: {value}. Expected format: YYYY-MM-DD")
        return value
    
    def get_days_count(self) -> int:
        """여행 일수 계산"""
        return (self.endDate - self.startDate).days + 1  # 시작일과 종료일 포함
    
    def create_query(self) -> str:
        """쿼리 생성"""
        days_count = self.get_days_count()
        query = f"{self.city}에서 {days_count} 동안 여행을 계획중입니다.\n"
        query += f"여행 기간은 {self.startDate}부터 {self.endDate} 입니다.\n"
        if self.preferActivity:
            query += f"사용자의 선호하는 활동은 '{self.preferActivity}'를 선호합니다.\n"
        if self.requirement:
            query += f"사용자의 추가적인 요청사항은 '{self.requirement}'입니다."
        query += f"{days_count * 2}개의 장소를 추천해주세요."
        return query

@router.post("/search", response_model=AttractionResponse)
async def search_attractions(request: AttractionSearchRequest) -> Dict[str, Any]:
    """
    어트랙션 검색 엔드포인트
    """
    try:
        result = await attraction_service.search_attractions(request.create_query())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.services.restaurant import RestaurantService, RestaurantResponse
from pydantic import BaseModel, validator
from datetime import datetime, date
from typing import Union

router = APIRouter(prefix="/api/v1/restaurants", tags=["restaurants"])
restaurant_service = RestaurantService()

# POST 요청을 위한 요청 모델 정의
class RestaurantSearchRequest(BaseModel):
    city: str
    startDate: date  # 날짜 형식으로 자동 변환
    endDate: date    # 날짜 형식으로 자동 변환
    preferActivity: Union[str, None] = None  # 문자열 또는 null 값 허용
    requirement: Union[str, None] = None     # 문자열 또는 null 값 허용
    preferFood: Union[str, None] = None  # 문자열 또는 null 값 허용
    dislikedFood: Union[str, None] = None  # 문자열 또는 null 값 허용
    ageRange: Union[str, None] = None  # 문자열 또는 null 값 허용
    numberOfPeople: Union[str, None] = None  # 문자열 또는 null 값 허용
    transportation: Union[str, None] = None  # 문자열 또는 null 값 허용
    
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
        query = f"{self.city}에서 {days_count}일 동안 여행을 계획중입니다.\n"
        query += f"여행 기간은 {self.startDate}부터 {self.endDate} 입니다.\n"
        
        # 여행자 정보
        if self.ageRange:
            query += f"여행자 정보: {self.ageRange}\n"
        if self.numberOfPeople:
            query += f"여행 인원: {self.numberOfPeople}\n"
        if self.transportation:
            query += f"교통수단: {self.transportation}\n"
        
        # 선호 활동
        if self.preferActivity:
            query += f"선호하는 활동: {self.preferActivity}\n"
        
        # 음식 관련 선호도
        if self.preferFood:
            query += f"선호하는 음식: {self.preferFood}\n"
        if self.dislikedFood:
            query += f"기피하는 음식: {self.dislikedFood}\n"
        
        # 추가 요구사항
        if self.requirement:
            query += f"추가 요구사항: {self.requirement}\n"
        
        query += f"\n위 조건들을 고려하여 {days_count * 3}개의 장소를 추천해주세요. "
        query += "각 장소에 대해 간단한 설명과 함께, 해당 장소가 왜 추천되는지 이유도 함께 알려주세요."
        return query

@router.post("/search", response_model=RestaurantResponse)
async def search_restaurants(request: RestaurantSearchRequest) -> Dict[str, Any]:
    """
    레스토랑 검색 엔드포인트
    """
    try:
        print("="*100)
        print(f"request.create_query(): {request.create_query()}")
        print("="*100)
        result = await restaurant_service.search_restaurants(request.create_query())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

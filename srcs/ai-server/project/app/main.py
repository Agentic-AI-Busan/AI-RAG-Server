from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import restaurant, other_service

app = FastAPI(title="Travel Agent API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(restaurant.router)
# app.include_router(other_service.router)  # 추후 다른 서비스 추가 시 사용


@app.get("/")
async def root():
    return {"message": "Travel Agent API is running"}

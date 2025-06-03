from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.routers import restaurant, attraction, query_router, other_service
from app.routers import restaurant_graph_rag_router
from app.routers import attraction_graph_rag_router
from app.utils import knowledge_graph_loader

# Lifespan 이벤트 핸들러 정의
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 애플리케이션 시작 시 실행
    print("애플리케이션 시작: 지식 그래프 로드를 시도합니다.")
    # knowledge_graph_loader 모듈의 load_knowledge_graph 함수를 호출하고,
    # 그 결과를 같은 모듈의 _graph_instance에 직접 할당합니다.
    knowledge_graph_loader._graph_instance = knowledge_graph_loader.load_knowledge_graph()
    
    # knowledge_graph_loader 모듈의 get_knowledge_graph 함수를 통해 상태 확인
    if knowledge_graph_loader.get_knowledge_graph():
        print("지식 그래프가 성공적으로 로드되었습니다.")
    else:
        print("경고: 지식 그래프 로드에 실패했습니다. 일부 기능이 제한될 수 있습니다.")
    yield
    # 애플리케이션 종료 시 실행 (필요시 정리 로직 추가)
    print("애플리케이션 종료.")

app = FastAPI(title="Agentic AI Busan API", lifespan=lifespan)

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
app.include_router(attraction.router)
app.include_router(query_router.router)
app.include_router(restaurant_graph_rag_router.router)
app.include_router(attraction_graph_rag_router.router)
# app.include_router(other_service.router)  # 추후 다른 서비스 추가 시 사용

@app.get("/")
async def root():
    return {"message": "Travel Agent API is running"}

@app.get("/health")
async def root():
    return {"status": "ok"}

@app.get("/graph-status") # 그래프 로드 상태 확인용 임시 엔드포인트
async def graph_status():
    # knowledge_graph_loader 모듈의 get_knowledge_graph 함수를 통해 상태 확인
    graph = knowledge_graph_loader.get_knowledge_graph()
    if graph:
        return {"status": "loaded", "nodes": graph.number_of_nodes(), "edges": graph.number_of_edges()}
    return {"status": "not_loaded_or_failed"}

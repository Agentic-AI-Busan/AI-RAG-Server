# Agentic AI Busan

## 프로젝트 소개
Agentic AI Busan은 부산 여행 정보를 제공하는 AI 기반 서비스입니다. 부산의 맛집, 관광지 등 다양한 정보를 자연어 질의응답 방식으로 제공하여 사용자들의 여행 계획을 돕습니다.

현재는 Naive RAG(Retrieval-Augmented Generation) 시스템으로 구현되어 있으며, 단계적으로 Advanced RAG, Modular RAG, 에이전트 시스템으로 발전시킬 계획입니다.

이 프로젝트는 [OKESTRO AGI(주)](https://www.lifelogm.co.kr/index.html)의 지원을 받았습니다.

## 시스템 아키텍처

### 현재 시스템 (Naive RAG)

```
+------------------+     +------------------+     +------------------+
|                  |     |                  |     |                  |
|  사용자 쿼리     +---->+  벡터 검색 (FAISS) +---->+  LLM 응답 생성   |
|                  |     |                  |     |                  |
+------------------+     +------------------+     +------------------+
```

시스템은 크게 두 부분으로 나뉩니다:
1. **ai-preprocessing**: 데이터 전처리 및 벡터 DB 생성
2. **ai-server**: 실제 API 서비스 제공 및 추론

## 주요 기능
- 부산 음식점, 관광지 정보 제공
- 자연어 질의에 대한 정확한 응답 생성

## 데이터
- [**부산관광공사 부산 음식테마거리**](https://data.busan.go.kr/bdip/opendata/detail.do?publicdatapk=15096646&searchKeyword=%EB%B6%80%EC%82%B0%EC%9D%8C%EC%8B%9D%ED%85%8C%EB%A7%88%EA%B1%B0%EB%A6%AC&searchOption=OR&from=dsh&uuid=181134f2-5d6a-42bb-b813-8932abc94847)
- [**부산관광공사 7 BEACH**](https://data.busan.go.kr/bdip/opendata/detail.do?publicdatapk=15096697&searchKeyword=7beach&searchOption=OR&uuid=c38581ed-925c-44a8-a0a7-f993b8bd5aad)
- [**부산광역시 부산명소정보**](https://data.busan.go.kr/bdip/opendata/detail.do?publicdatapk=15063481&searchKeyword=%EB%B6%80%EC%82%B0%20%EB%AA%85%EC%86%8C&searchOption=OR&uuid=4b435728-23f2-4bae-a236-791295496b57)
- **데이터 정제 과정**:
  1. 원본 데이터 수집
  2. 필요 없는 데이터 제거
  3. 요약 및 마크다운 형식으로 정제
  4. 벡터 임베딩 생성 및 FAISS 인덱스 구축

## 기술 스택
- **FastAPI**: 백엔드 API 서버
- **LangChain**: RAG 및 에이전트 프레임워크
- **FAISS**: 벡터 데이터베이스
- **OpenAI API**: 텍스트 생성 및 임베딩
- **Docker**: 컨테이너화 및 배포

## 설치 및 실행 방법

### 준비사항
1. Docker Desktop 설치
2. OpenAI API 키 준비

### 설치 과정
1. 프로젝트 클론
   ```
   git clone [repository-url]
   ```
2. 환경 변수 설정
   - `.env.local` 파일의 내용을 확인하고 필요한 API 키 설정
   - 파일 이름을 `.env`로 변경

### 실행 방법
- Windows:
  ```
  docker compose up --build -d
  ```
- Mac:
  ```
  make
  ```

### API 테스트
- 웹 브라우저에서 `localhost:80` 접속
- 예시 API 호출:
  ```
  localhost:80/api/v1/restaurants/search?query="부산고기맛집 추천"
  ```

## 업그레이드 로드맵
1. **Advanced RAG**: 재순위화, 하이브리드 검색, 의미론적 쿼리 확장 등
2. **Modular RAG**: 다중 벡터 스토어 통합, 라우터 패턴, 그래프 기반 RAG 등
3. **Agent System**: 외부 API 통합, 여행 계획 자동 생성 등

## 프로젝트 구조
```
project_root/
├── ai-preprocessing/   # 데이터 전처리 및 벡터 DB 생성
│   ├── Dockerfile
│   ├── requirements.txt
│   └── project/
│       └── script/
│           └── create_restaurant_vectordb.py
├── ai-server/          # API 서버 및 추론
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── requirements.txt
│   └── project/
│       ├── app/
│       │   ├── main.py
│       │   ├── routers/
│       │   ├── services/
│       │   └── utils/
│       └── vectordb/
├── docs/               # 기술 문서
│   ├── naive_rag_implementation.md
│   └── testing_guide.md
├── docker-compose.yml
└── README.md
```

## 개발자 정보
<table>
    <tr height="160px">
        <td align="center" width="160px">
            <a href="https://github.com/KJ-Min"><img height="120px" width="120px" src="https://avatars.githubusercontent.com/KJ-Min"/></a>
            <br/>
            <a href="https://github.com/KJ-Min"><strong>민경진</strong></a>
            <br />
        </td>
        <td>
            <strong><프로젝트 기여></strong><br/>
            • 약 60K 음식점 벡터 데이터베이스 구축<br/>
            • LLM 리서치<br/>
            • RAG 시스템 설계 및 구현<br/>
            • 데이터 파이프라인 개발
        </td>
    </tr>
</table>
<table>
    <tr height="160px">
        <td align="center" width="160px">
            <a href="https://github.com/JeongTJ"><img height="120px" width="120px" src="https://avatars.githubusercontent.com/JeongTJ"/></a>
            <br/>
            <a href="https://github.com/JeongTJ"><strong>정태준</strong></a>
            <br />
        </td>   
        <td>
            <strong><프로젝트 기여></strong><br/>
            • 관광지 벡터 데이터베이스 구축<br/>
            • RAG 시스템 구현<br/>
            • Docker 파이프라인 개발<br/>
            • Github Action CI/CD 구축
        </td> 
    </tr>
</table>
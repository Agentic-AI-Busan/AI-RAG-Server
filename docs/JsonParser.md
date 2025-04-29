# JSON 파서 시스템 문서

## 개요
이 문서는 AI 서버에서 사용되는 JSON 파서 시스템에 대해 설명합니다. JSON 파서는 LLM의 응답을 구조화된 JSON 형식으로 변환하고 검증하는 역할을 합니다.

## JSON 파서 구조

### 기본 응답 모델
모든 서비스는 공통된 기본 응답 구조를 사용합니다:

```python
class Recommendation(BaseModel):
    name: str        # 장소 이름
    description: str # 장소에 대한 설명
    index: int       # 장소 인덱스

class ServiceResponse(BaseModel):
    recommendations: List[Recommendation]  # 추천 장소 리스트
    service_ids: List[int]                 # 백엔드에서 요청하는 장소 ID
```

### 파서 초기화
각 서비스는 다음과 같이 JSON 파서를 초기화합니다:
```python
self.parser = JsonOutputParser(pydantic_object=ServiceResponse)
```

## 파서 체인 구성

### 프롬프트 템플릿
각 서비스는 다음과 같은 구조의 프롬프트를 사용합니다:
```python
prompt = ChatPromptTemplate.from_messages([
    ("system", """
    당신은 [서비스] 추천 AI입니다. 주어진 맥락을 바탕으로 사용자의 질문에 답변해주세요.
    
    다음 지침을 따라 답변해주세요:
    1. 각 문서 처음에 있는 대괄호 부분은 인덱스 번호 입니다.
    2. 사용자 질문에 맞는 [서비스]를 선택하여 name과 description과 index 형태로 제공해주세요.
    3. 선택한 [서비스]의 인덱스 번호를 [service]_ids 리스트에 포함해주세요.
    4. 반드시 지정된 JSON 형식으로 응답해주세요.
    """),
    ("user", "[서비스] 정보: {service_info}\n\n사용자 질문: {user_request}\n\n{format_instructions}")
])
```

### 체인 구성
파서 체인은 다음과 같이 구성됩니다:
```python
self.chain = self.prompt | self.llm | self.parser
```

## 응답 처리 과정

1. **문서 검색 및 인덱싱**
```python
docs = await self.retriever.aretrieve(query)
context = ""
for index, doc in enumerate(docs):
    context += f"[{index}]: "
    context += doc.page_content + "\n\n"
```

2. **LLM 응답 생성 및 파싱**
```python
response = await self.chain.ainvoke({
    "service_info": context, 
    "user_request": query
})
```

3. **응답 검증**
```python
def response_validation_check(self, docs, response):
    original_recommandations = response.get("recommendations", [])
    for rec in original_recommandations:
        index = rec.get("index", -1)
        if 0 <= index < len(docs):
            # 문서 내용과 LLM 응답 내용 비교
            markdown_content = docs[index].page_content
            # ... 검증 로직 ...
```

4. **ID 변환**
```python
original_ids = response.get("service_ids", [])
content_ids = []
for index in original_ids:
    if 0 <= index < len(docs):
        content_id = docs[index].metadata.get("content_id")
        if content_id:
            content_ids.append(content_id)
response["service_ids"] = content_ids
```

## 서비스별 특화 사항

### 어트랙션 서비스
- `content_id`를 메타데이터에서 추출
- 관광지 정보에 특화된 프롬프트 사용

### 레스토랑 서비스
- `RSTR_ID`를 메타데이터에서 추출
- 식당 정보에 특화된 프롬프트 사용

## 오류 처리
- LLM 호출 실패 시 기본 응답 반환
- 인덱스 범위 검증
- 메타데이터 존재 여부 확인

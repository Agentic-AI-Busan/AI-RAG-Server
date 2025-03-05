import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document

# 환경변수 로드
load_dotenv()


def prepare_restaurant_documents(docs):
    restaurant_docs = []
    for doc in docs:
        content = doc.page_content

        # RSTR_ID 값 추출
        rstr_id = None
        for line in content.split("\n"):
            if line.startswith("\ufeffRSTR_ID:") or line.startswith("RSTR_ID:"):
                rstr_id = int(line.split(":")[1].strip())
                break

        # RSTR_ID 줄을 제외한 나머지 내용만 포함
        content_lines = [
            line
            for line in content.split("\n")
            if not (line.startswith("\ufeffRSTR_ID:") or line.startswith("RSTR_ID:"))
        ]
        filtered_content = "\n".join(content_lines)

        restaurant_docs.append(
            Document(
                page_content=filtered_content.strip(), metadata={"RSTR_ID": rstr_id}
            )
        )

    return restaurant_docs


def create_vectordb(
    data_path: str | Path, index_name: str, encoding: str = "utf-8"
) -> None:
    """벡터 DB를 생성하고 저장합니다."""
    # 프로젝트 루트 디렉토리 찾기
    project_root = Path(__file__).parent.parent

    # 절대 경로로 변환
    data_path = project_root / data_path

    print(f"프로젝트 루트 디렉토리: {project_root}")
    print(f"데이터 파일 경로: {data_path}")

    if not data_path.exists():
        raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {data_path}")

    # 데이터 로드 및 전처리
    loader = CSVLoader(file_path=str(data_path), encoding=encoding)
    docs = loader.load()

    # 문서 전처리 수행
    processed_docs = prepare_restaurant_documents(docs)
    print(f"처리된 문서 수: {len(processed_docs)}")

    vectordb_path = project_root / "vectordb" / index_name
    vectordb_path.parent.mkdir(exist_ok=True)

    # 전처리된 문서로 벡터스토어 생성
    vectorstore = FAISS.from_documents(
        documents=processed_docs, embedding=OpenAIEmbeddings()
    )

    vectorstore.save_local(str(vectordb_path))
    print(f"벡터 DB가 성공적으로 저장되었습니다: {vectordb_path}")


if __name__ == "__main__":
    # 레스토랑 벡터 DB 생성
    create_vectordb(
        data_path="data/food/음식테마거리/RAG_TEST_with_summary.csv",
        index_name="restaurant_finder",
    )

    # 추후 다른 서비스의 벡터 DB 생성도 여기에 추가

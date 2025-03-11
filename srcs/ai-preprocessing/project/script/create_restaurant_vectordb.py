import os
import sys
from tqdm import tqdm
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
import pandas as pd

# 환경변수 로드
load_dotenv()

CHUNK_SIZE = 500  # 한 번에 처리할 CSV 행 수

def split_csv(input_path: Path, output_prefix: str, chunk_size: int = CHUNK_SIZE):
    """큰 CSV 파일을 여러 개로 분할"""
    output_files = []
    for i, chunk in enumerate(pd.read_csv(input_path, chunksize=chunk_size, encoding="utf-8")):
        output_file = input_path.parent / f"{output_prefix}_part{i}.csv"
        chunk.to_csv(output_file, index=False)
        output_files.append(output_file)
    return output_files


def prepare_restaurant_documents(docs):
    """CSV 데이터를 벡터화할 문서 형태로 변환"""
    restaurant_docs = []
    for doc in docs:
        content = doc.page_content
        rstr_id = None

        for line in content.split("\n"):
            if line.startswith("\ufeffRSTR_ID:") or line.startswith("RSTR_ID:"):
                try:
                    rstr_id = int(line.split(":")[1].strip())
                except ValueError:
                    rstr_id = None  # 변환 실패 시 None으로 설정
                break

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


def create_vectordb(data_path: str | Path, index_name: str, encoding: str = "utf-8") -> None:
    """벡터 DB를 생성하고 저장"""
    project_root = Path(__file__).parent.parent
    data_path = project_root / data_path

    if not data_path.exists():
        raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {data_path}")

    vectordb_path = project_root / "vectordb" / index_name
    vectordb_path.parent.mkdir(exist_ok=True, parents=True)

    # 기존 벡터DB 로드 (이미 있는 경우)
    embeddings = OpenAIEmbeddings()
    vectorstore = None

    if vectordb_path.exists():
        print("기존 벡터DB를 로드합니다...")
        try:
            vectorstore = FAISS.load_local(str(vectordb_path), embeddings, allow_dangerous_deserialization=True)
        except Exception as e:
            print(f"벡터DB 로드 실패: {e}")
            vectorstore = None

    # CSV 파일 분할
    print(f"파일이 너무 커서 분할 진행... (기본 {CHUNK_SIZE}행씩)")
    split_files = split_csv(data_path, index_name)

    # 분할된 CSV 파일 하나씩 처리
    for file in tqdm(split_files, desc="Embedding 중"):
        print(f"처리 중: {file}")
        loader = CSVLoader(file_path=str(file), encoding=encoding)
        docs = loader.load()

        processed_docs = prepare_restaurant_documents(docs)
        print(f"처리된 문서 수: {len(processed_docs)}")

        # 문서 임베딩 생성
        # embedded_documents = [
        #     (doc, embeddings.embed_query(doc.page_content)) for doc in tqdm(processed_docs, desc="Embedding 중")
        # ]

        # FAISS 벡터DB 생성
        new_vectorstore = FAISS.from_documents(
            documents=processed_docs, embedding=OpenAIEmbeddings()
        )
        # new_vectorstore = FAISS.from_embeddings(
        #     texts=[doc.page_content for doc, _ in embedded_documents],  # ✅ 문서 텍스트 추가
        #     embeddings=[embed for _, embed in embedded_documents],      # ✅ 임베딩 벡터 추가
        #     embedding=embeddings  # ✅ OpenAIEmbeddings 인스턴스 추가
        # )

        # 기존 벡터DB와 병합
        if vectorstore:
            vectorstore.merge_from(new_vectorstore)
        else:
            vectorstore = new_vectorstore

    for file in split_files:
        # 임시 파일 삭제
        os.remove(file)

    # 벡터DB 저장
    if vectorstore:
        vectorstore.save_local(str(vectordb_path))
        print(f"벡터 DB 저장 완료: {vectordb_path}")
    else:
        print("⚠️ 벡터DB 저장할 데이터가 없습니다!")


if __name__ == "__main__":
    data_path = sys.argv[1]
    create_vectordb(data_path=data_path, index_name="restaurant_finder")

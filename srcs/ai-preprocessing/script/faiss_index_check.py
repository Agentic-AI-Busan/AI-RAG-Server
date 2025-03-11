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

def print_vectordb_info(data_path: str | Path, encoding: str = "utf-8") -> None:
    """벡터 DB를 생성하고 저장"""
    project_root = Path(__file__).parent.parent
    data_path = project_root / data_path

    if not data_path.exists():
        raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {data_path}")

    # 기존 벡터DB 로드 (이미 있는 경우)
    embeddings = OpenAIEmbeddings()
    vectorstore = None

    if data_path.exists():
        print("기존 벡터DB를 로드합니다...")
        try:
            vectorstore = FAISS.load_local(str(data_path), embeddings, allow_dangerous_deserialization=True)
        except Exception as e:
            print(f"벡터DB 로드 실패: {e}")
            vectorstore = None
    print(vectorstore.index.ntotal)


if __name__ == "__main__":
    data_path = sys.argv[1]
    print_vectordb_info(data_path=data_path)

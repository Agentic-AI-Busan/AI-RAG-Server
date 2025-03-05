import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 파이썬 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.utils.vectordb import load_vectordb


def test_vectordb_load():
    try:
        vectorstore = load_vectordb("restaurant_finder")
        print("벡터 DB 로드 성공!")

        # 간단한 검색 테스트
        results = vectorstore.similarity_search("부산 맛집", k=1)
        print("\n검색 결과 샘플:")
        print(results[0].page_content[:200])

    except Exception as e:
        print(f"오류 발생: {str(e)}")


if __name__ == "__main__":
    test_vectordb_load()

from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings


def load_vectordb(index_name: str):
    """
    저장된 벡터 DB를 로드합니다.

    Args:
        index_name (str): 벡터 DB 이름 (예: "restaurant_finder")

    Returns:
        FAISS: 로드된 벡터스토어 객체
    """
    try:
        # 프로젝트 루트 디렉토리 찾기
        project_root = Path(__file__).parent.parent.parent
        vectordb_path = project_root / "vectordb" / index_name

        if not vectordb_path.exists():
            raise FileNotFoundError(f"Vector DB not found at {vectordb_path}")

        vectorstore = FAISS.load_local(
            str(vectordb_path),
            embeddings=OpenAIEmbeddings(),
            allow_dangerous_deserialization=True,  # 안전한 소스에서 로드하므로 허용
        )
        return vectorstore
    except Exception as e:
        print("="*10)
        print("error: ", e)
        print("="*10)
        
        raise Exception(f"벡터 DB 로드 중 오류 발생: {e}")

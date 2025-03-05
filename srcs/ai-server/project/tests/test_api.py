# test_api.py
import requests


def test_restaurant_search():
    url = "http://localhost:8000/api/v1/restaurants/search"
    query = "부산에서 해산물 맛집 추천해주세요"

    try:
        response = requests.get(url, params={"query": query})
        response.raise_for_status()  # 에러 발생시 예외 발생
        result = response.json()
        print("응답 결과:", result)
        return result
    except requests.exceptions.RequestException as e:
        print(f"API 요청 중 오류 발생: {e}")
        if hasattr(e.response, "json"):
            print("에러 상세:", e.response.json())
        return None


if __name__ == "__main__":
    test_restaurant_search()

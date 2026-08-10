from typing import List
from sources.base import BaseNewsSource, NewsArticle

class KakaoNewsAPISource(BaseNewsSource):
    """카카오 뉴스 검색 API 수집기 스텁"""

    def __init__(self, rest_api_key: str, queries: List[str] = None, category: str = "경제"):
        self.api_key = rest_api_key
        self.queries = queries or ["경제", "글로벌"]
        self.category = category

    @property
    def source_name(self) -> str:
        return "카카오 뉴스 검색 API"

    @property
    def source_type(self) -> str:
        return "kakao_api"

    def fetch_articles(self) -> List[NewsArticle]:
        if not self.api_key:
            print(f"[{self.source_name}] API 키가 설정되지 않아 건너뜁니다.")
            return []
        
        # TODO: GET https://dapi.kakao.com/v2/search/news 연동 구현
        print(f"[{self.source_name}] API 연동 스텁 호출됨 (향후 API 키 등록 시 자동 동작)")
        return []

class NewsAPISource(BaseNewsSource):
    """NewsAPI.org 수집기 스텁"""

    def __init__(self, api_key: str, country: str = "kr", category: str = "business"):
        self.api_key = api_key
        self.country = country
        self.category = category

    @property
    def source_name(self) -> str:
        return "NewsAPI.org"

    @property
    def source_type(self) -> str:
        return "newsapi"

    def fetch_articles(self) -> List[NewsArticle]:
        if not self.api_key:
            print(f"[{self.source_name}] API 키가 설정되지 않아 건너뜁니다.")
            return []

        # TODO: GET https://newsapi.org/v2/top-headlines 연동 구현
        print(f"[{self.source_name}] API 연동 스텁 호출됨 (향후 API 키 등록 시 자동 동작)")
        return []

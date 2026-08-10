import requests
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
        
        print(f"[{self.source_name}] API 연동 스텁 호출됨 (향후 API 키 등록 시 자동 동작)")
        return []

class NewsAPISource(BaseNewsSource):
    """NewsAPI.org 뉴스 수집기 연동"""

    def __init__(self, api_key: str):
        self.api_key = api_key

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

        articles: List[NewsArticle] = []

        # 1. 경제 카테고리 (Top Business Headlines for Korea)
        try:
            biz_url = f"https://newsapi.org/v2/top-headlines?country=kr&category=business&pageSize=20&apiKey={self.api_key}"
            resp = requests.get(biz_url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("articles", []):
                    title = item.get("title", "")
                    if not title or title == "[Removed]":
                        continue
                    pub_name = item.get("source", {}).get("name", "NewsAPI")
                    articles.append(NewsArticle(
                        title=title,
                        publisher=pub_name,
                        url=item.get("url", ""),
                        summary=item.get("description", "") or "",
                        full_content=item.get("content", "") or item.get("description", "") or "",
                        target_category="경제",
                        source_type=self.source_type,
                        published_at=item.get("publishedAt", ""),
                        thumbnail_url=item.get("urlToImage", "") or ""
                    ))
                print(f"[{self.source_name}] 경제 수집 완료: {len(articles)}개 기사")
            else:
                print(f"[{self.source_name}] 경제 수집 응답 실패 ({resp.status_code})")
        except Exception as e:
            print(f"[{self.source_name}] 경제 수집 중 예외 발생: {e}")

        # 2. 글로벌 카테고리 (Everything search with global keywords in Korean)
        try:
            global_url = f"https://newsapi.org/v2/everything?q=글로벌 OR 세계 OR 환율 OR 미증시&language=ko&sortBy=publishedAt&pageSize=15&apiKey={self.api_key}"
            resp = requests.get(global_url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                initial_count = len(articles)
                for item in data.get("articles", []):
                    title = item.get("title", "")
                    if not title or title == "[Removed]":
                        continue
                    pub_name = item.get("source", {}).get("name", "NewsAPI")
                    articles.append(NewsArticle(
                        title=title,
                        publisher=pub_name,
                        url=item.get("url", ""),
                        summary=item.get("description", "") or "",
                        full_content=item.get("content", "") or item.get("description", "") or "",
                        target_category="글로벌",
                        source_type=self.source_type,
                        published_at=item.get("publishedAt", ""),
                        thumbnail_url=item.get("urlToImage", "") or ""
                    ))
                print(f"[{self.source_name}] 글로벌 수집 완료: {len(articles) - initial_count}개 기사")
            else:
                print(f"[{self.source_name}] 글로벌 수집 응답 실패 ({resp.status_code})")
        except Exception as e:
            print(f"[{self.source_name}] 글로벌 수집 중 예외 발생: {e}")

        return articles

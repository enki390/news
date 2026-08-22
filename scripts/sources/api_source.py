import requests
import re
from bs4 import BeautifulSoup
from typing import List
from sources.base import BaseNewsSource, NewsArticle
from config import HTTP_HEADERS

class KakaoNewsAPISource(BaseNewsSource):
    """카카오 뉴스 검색 API 수집기 스텁"""

    def __init__(self, rest_api_key: str, queries: List[str] = None, category: str = "경제"):
        self.api_key = rest_api_key
        self.queries = queries or ["경제", "글로벌", "비즈니스", "IT"]
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
    """NewsAPI.org 뉴스 수집기 연동 (원문 URL 웹 크롤링을 통한 기사 본문 전체 수집)"""

    def __init__(self, api_key: str):
        self.api_key = api_key

    @property
    def source_name(self) -> str:
        return "NewsAPI.org"

    @property
    def source_type(self) -> str:
        return "newsapi"

    def _extract_full_article_content(self, url: str, raw_content: str, description: str) -> str:
        """기사 원본 URL 접속 후 전체 본문을 크롤링하여 추출 (실패 시 Fallback 청소 처리)"""
        if url and url.startswith("http"):
            try:
                resp = requests.get(url, headers=HTTP_HEADERS, timeout=6)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    # 불필요 스크립트, 스타일 태그 제거
                    for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                        element.decompose()

                    paragraphs = soup.find_all('p')
                    body_paras = []
                    for p in paragraphs:
                        txt = p.get_text().strip()
                        if len(txt) > 25 and not any(skip in txt for skip in ["무단 전재", "재배포 금지", "Copyright", "All rights reserved"]):
                            body_paras.append(txt)

                    if len(body_paras) >= 2:
                        full_body = "\n\n".join(body_paras)
                        print(f"[{self.source_name}] 원문 웹 크롤링 본문 추출 성공 ({len(full_body)}자)")
                        return full_body
            except Exception as e:
                print(f"[{self.source_name}] 원문 크롤링 시도 예외 ({url}): {e}")

        # Fallback: NewsAPI의 [+... chars] 및 truncate 문구 제거
        cleaned = raw_content or description or ""
        cleaned = re.sub(r'\[\+\d+\s+chars\]', '', cleaned).strip()
        return cleaned

    def fetch_articles(self) -> List[NewsArticle]:
        if not self.api_key:
            print(f"[{self.source_name}] API 키가 설정되지 않아 건너뜁니다.")
            return []

        articles: List[NewsArticle] = []

        # 1. 경제 / 비즈니스 카테고리 (Top Business Headlines for Korea)
        try:
            biz_url = f"https://newsapi.org/v2/top-headlines?country=kr&category=business&pageSize=15&apiKey={self.api_key}"
            resp = requests.get(biz_url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("articles", []):
                    title = item.get("title", "")
                    if not title or title == "[Removed]":
                        continue
                    pub_name = item.get("source", {}).get("name", "NewsAPI")
                    article_url = item.get("url", "")
                    description = item.get("description", "") or ""
                    raw_content = item.get("content", "") or ""

                    full_body = self._extract_full_article_content(article_url, raw_content, description)

                    articles.append(NewsArticle(
                        title=title,
                        publisher=pub_name,
                        url=article_url,
                        summary=description,
                        full_content=full_body,
                        target_category="경제",
                        source_type=self.source_type,
                        published_at=item.get("publishedAt", ""),
                        thumbnail_url=item.get("urlToImage", "") or ""
                    ))
                print(f"[{self.source_name}] 경제/비즈니스 수집 완료: {len(articles)}개 기사")
            else:
                print(f"[{self.source_name}] 경제 수집 응답 실패 ({resp.status_code})")
        except Exception as e:
            print(f"[{self.source_name}] 경제 수집 중 예외 발생: {e}")

        # 2. 글로벌 카테고리 (Everything search with global keywords in Korean)
        try:
            global_url = f"https://newsapi.org/v2/everything?q=글로벌 OR 세계 OR 환율 OR 미증시&language=ko&sortBy=publishedAt&pageSize=10&apiKey={self.api_key}"
            resp = requests.get(global_url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                initial_count = len(articles)
                for item in data.get("articles", []):
                    title = item.get("title", "")
                    if not title or title == "[Removed]":
                        continue
                    pub_name = item.get("source", {}).get("name", "NewsAPI")
                    article_url = item.get("url", "")
                    description = item.get("description", "") or ""
                    raw_content = item.get("content", "") or ""

                    full_body = self._extract_full_article_content(article_url, raw_content, description)

                    articles.append(NewsArticle(
                        title=title,
                        publisher=pub_name,
                        url=article_url,
                        summary=description,
                        full_content=full_body,
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

        # 3. IT/과학 카테고리 (Technology / Science headlines)
        try:
            tech_url = f"https://newsapi.org/v2/top-headlines?country=kr&category=technology&pageSize=15&apiKey={self.api_key}"
            resp = requests.get(tech_url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                initial_count = len(articles)
                for item in data.get("articles", []):
                    title = item.get("title", "")
                    if not title or title == "[Removed]":
                        continue
                    pub_name = item.get("source", {}).get("name", "NewsAPI")
                    article_url = item.get("url", "")
                    description = item.get("description", "") or ""
                    raw_content = item.get("content", "") or ""

                    full_body = self._extract_full_article_content(article_url, raw_content, description)

                    articles.append(NewsArticle(
                        title=title,
                        publisher=pub_name,
                        url=article_url,
                        summary=description,
                        full_content=full_body,
                        target_category="IT/과학",
                        source_type=self.source_type,
                        published_at=item.get("publishedAt", ""),
                        thumbnail_url=item.get("urlToImage", "") or ""
                    ))
                print(f"[{self.source_name}] IT/과학 수집 완료: {len(articles) - initial_count}개 기사")
            else:
                print(f"[{self.source_name}] IT/과학 수집 응답 실패 ({resp.status_code})")
        except Exception as e:
            print(f"[{self.source_name}] IT/과학 수집 중 예외 발생: {e}")

        return articles

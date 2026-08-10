from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

@dataclass
class NewsArticle:
    """통합 뉴스 기사 데이터 클래스"""
    title: str
    publisher: str
    url: str
    summary: str = ""
    full_content: str = ""
    target_category: str = "경제"
    source_type: str = "rss"
    published_at: str = ""
    thumbnail_url: str = ""

    def to_dict(self):
        return {
            "title": self.title,
            "publisher": self.publisher,
            "url": self.url,
            "summary": self.summary,
            "full_content": self.full_content,
            "target_category": self.target_category,
            "source_type": self.source_type,
            "published_at": self.published_at,
            "thumbnail_url": self.thumbnail_url
        }

class BaseNewsSource(ABC):
    """뉴스 소스 추상 베이스 클래스"""
    @abstractmethod
    def fetch_articles(self) -> List[NewsArticle]:
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        pass

    @property
    @abstractmethod
    def source_type(self) -> str:
        pass

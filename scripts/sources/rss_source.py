from typing import List
import feedparser
from sources.base import BaseNewsSource, NewsArticle
from utils import clean_html, parse_publisher_from_title, fetch_article_content

class RSSNewsSource(BaseNewsSource):
    """RSS 피드 기반 뉴스 수집기"""

    def __init__(self, feeds_config, enable_crawling=False, max_articles_per_feed=8):
        self.feeds = feeds_config
        self.enable_crawling = enable_crawling
        self.max_per_feed = max_articles_per_feed

    @property
    def source_name(self) -> str:
        return "RSS Feeds"

    @property
    def source_type(self) -> str:
        return "rss"

    def fetch_articles(self) -> List[NewsArticle]:
        articles = []
        print(f"[{self.source_name}] RSS 피드 수집 시작 (피드 수: {len(self.feeds)}, 크롤링: {self.enable_crawling})...")

        for feed_info in self.feeds:
            try:
                print(f"  - 수집 중: [{feed_info['category']}] {feed_info['name']}...")
                feed = feedparser.parse(feed_info['url'])
                count = 0
                for entry in feed.entries:
                    if count >= self.max_per_feed:
                        break
                    title = entry.get('title', '')
                    link = entry.get('link', '')
                    summary_raw = entry.get('summary', entry.get('description', ''))
                    published = entry.get('published', entry.get('updated', ''))

                    if not title or not link:
                        continue

                    clean_title, pub_name = parse_publisher_from_title(title, feed_info['name'])
                    summary_clean = clean_html(summary_raw)

                    effective_content = ""
                    if self.enable_crawling:
                        full_body = fetch_article_content(link)
                        if full_body and len(full_body) > 50:
                            effective_content = full_body

                    if not effective_content:
                        if summary_clean and len(summary_clean) > 30:
                            effective_content = summary_clean
                        else:
                            effective_content = clean_title

                    articles.append(NewsArticle(
                        title=clean_title,
                        publisher=pub_name,
                        url=link,
                        summary=summary_clean[:300],
                        full_content=effective_content[:2000],
                        target_category=feed_info['category'],
                        source_type="rss",
                        published_at=str(published)
                    ))
                    count += 1
            except Exception as e:
                print(f"    Warning: Failed to fetch {feed_info['name']}: {e}")

        print(f"[{self.source_name}] 총 수집된 기사 수: {len(articles)}")
        return articles

import os
import json
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RETENTION_DAYS = 30

# Rules
ALLOWED_CATEGORIES = ["경제", "글로벌"]
MAX_ARTICLES_PER_FEED = 8
MAX_CLUSTERS = 10
ENABLE_WEB_CRAWLING = True  # Enable web crawling for full article body extraction

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
}

# Default RSS Feeds (공식 RSS 및 메인 방송사 구글 뉴스 RSS 피드)
DEFAULT_FEEDS = [
    # --- 경제 (Economy) ---
    {"name": "연합뉴스", "category": "경제", "url": "https://www.yna.co.kr/rss/economy.xml"},
    {"name": "매일경제", "category": "경제", "url": "https://www.mk.co.kr/rss/30000001/"},
    {"name": "한국경제", "category": "경제", "url": "https://www.hankyung.co.kr/feed/economy"},
    {"name": "경향신문", "category": "경제", "url": "https://www.khan.co.kr/rss/rssdata/economy.xml"},
    {"name": "한겨레", "category": "경제", "url": "https://www.hani.co.kr/rss/economy/"},
    {"name": "SBS", "category": "경제", "url": "https://news.sbs.co.kr/news/sectionRssFeed.do?sectionId=02"},
    {"name": "KBS", "category": "경제", "url": "https://news.google.com/rss/search?q=site:news.kbs.co.kr+경제&hl=ko&gl=KR&ceid=KR:ko"},
    {"name": "MBC", "category": "경제", "url": "https://news.google.com/rss/search?q=site:imnews.imbc.com+경제&hl=ko&gl=KR&ceid=KR:ko"},
    {"name": "YTN", "category": "경제", "url": "https://news.google.com/rss/search?q=site:ytn.co.kr+경제&hl=ko&gl=KR&ceid=KR:ko"},

    # --- 글로벌 (Global) ---
    {"name": "연합뉴스", "category": "글로벌", "url": "https://www.yna.co.kr/rss/international.xml"},
    {"name": "매일경제", "category": "글로벌", "url": "https://www.mk.co.kr/rss/30200030/"},
    {"name": "한국경제", "category": "글로벌", "url": "https://www.hankyung.co.kr/feed/international"},
    {"name": "경향신문", "category": "글로벌", "url": "https://www.khan.co.kr/rss/rssdata/kh_world.xml"},
    {"name": "한겨레", "category": "글로벌", "url": "https://www.hani.co.kr/rss/international/"},
    {"name": "SBS", "category": "글로벌", "url": "https://news.sbs.co.kr/news/sectionRssFeed.do?sectionId=09"},
    {"name": "KBS", "category": "글로벌", "url": "https://news.google.com/rss/search?q=site:news.kbs.co.kr+국제|글로벌&hl=ko&gl=KR&ceid=KR:ko"},
    {"name": "MBC", "category": "글로벌", "url": "https://news.google.com/rss/search?q=site:imnews.imbc.com+국제|글로벌&hl=ko&gl=KR&ceid=KR:ko"},
    {"name": "YTN", "category": "글로벌", "url": "https://news.google.com/rss/search?q=site:ytn.co.kr+국제|글로벌&hl=ko&gl=KR&ceid=KR:ko"}
]

# API Keys & Flags
KAKAO_REST_API_KEY = os.environ.get("KAKAO_REST_API_KEY", "")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", os.environ.get("NEWSAPI_KEY", ""))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    config_file = DATA_DIR / "config.json"
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                GEMINI_API_KEY = cfg.get("gemini_api_key", cfg.get("GEMINI_API_KEY", ""))
        except Exception:
            pass

COLLECT_MODE = os.environ.get("COLLECT_MODE", "collect")

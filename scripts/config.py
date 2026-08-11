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
MAX_CLUSTERS = 20
ENABLE_WEB_CRAWLING = False  # 기본 RSS summary 사용, 필요 시 True

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
}

# RSS Feeds (경제 15개, 글로벌 10개)
RSS_FEEDS = [
    # 1. 경제
    {"category": "경제", "name": "매일경제", "url": "https://www.mk.co.kr/rss/30000001/"},
    {"category": "경제", "name": "한국경제", "url": "https://www.hankyung.com/feed/economy"},
    {"category": "경제", "name": "서울경제", "url": "https://www.sedaily.com/RSS/Economy/"},
    {"category": "경제", "name": "머니투데이", "url": "https://rss.mt.co.kr/mt/mtview/money/"},
    {"category": "경제", "name": "이데일리", "url": "https://rss.edaily.co.kr/edaily/economy.xml"},
    {"category": "경제", "name": "파이낸셜뉴스", "url": "https://www.fnnews.com/rss/fn_economy.xml"},
    {"category": "경제", "name": "아시아경제", "url": "https://www.asiae.co.kr/rss/economy.xml"},
    {"category": "경제", "name": "조선일보", "url": "https://www.chosun.com/arc/outboundfeeds/rss/category/economy/"},
    {"category": "경제", "name": "중앙일보", "url": "https://rss.joins.com/joins_economy_list.xml"},
    {"category": "경제", "name": "동아일보", "url": "https://rss.donga.com/economy.xml"},
    {"category": "경제", "name": "한겨레", "url": "https://www.hani.co.kr/rss/economy/"},
    {"category": "경제", "name": "경향신문", "url": "https://www.khan.co.kr/rss/rssdata/economy.xml"},
    {"category": "경제", "name": "연합뉴스", "url": "https://www.yna.co.kr/rss/economy.xml"},
    {"category": "경제", "name": "뉴시스", "url": "https://newsis.com/RSS/economy.xml"},
    {"category": "경제", "name": "Google News 경제", "url": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko"},

    # 2. 글로벌
    {"category": "글로벌", "name": "조선일보", "url": "https://www.chosun.com/arc/outboundfeeds/rss/category/international/"},
    {"category": "글로벌", "name": "중앙일보", "url": "https://rss.joins.com/joins_world_list.xml"},
    {"category": "글로벌", "name": "동아일보", "url": "https://rss.donga.com/international.xml"},
    {"category": "글로벌", "name": "한겨레", "url": "https://www.hani.co.kr/rss/international/"},
    {"category": "글로벌", "name": "경향신문", "url": "https://www.khan.co.kr/rss/rssdata/kh_world.xml"},
    {"category": "글로벌", "name": "연합뉴스", "url": "https://www.yna.co.kr/rss/international.xml"},
    {"category": "글로벌", "name": "뉴시스", "url": "https://newsis.com/RSS/international.xml"},
    {"category": "글로벌", "name": "KBS 글로벌", "url": "https://world.kbs.co.kr/rss/rss_news.htm?lang=k"},
    {"category": "글로벌", "name": "SBS 글로벌", "url": "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=08"},
    {"category": "글로벌", "name": "Google News 글로벌", "url": "https://news.google.com/rss/headlines/section/topic/WORLD?hl=ko&gl=KR&ceid=KR:ko"}
]

# API Keys & Flags
KAKAO_REST_API_KEY = os.environ.get("KAKAO_REST_API_KEY", "")
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "e38b4843e5aa4d6f994d069eb1cc8f8a")
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

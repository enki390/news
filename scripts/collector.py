import os
import json
import datetime
from pathlib import Path

from config import (
    RSS_FEEDS, ENABLE_WEB_CRAWLING, MAX_ARTICLES_PER_FEED,
    KAKAO_REST_API_KEY, NEWSAPI_KEY, COLLECT_MODE, DATA_DIR
)
from sources.rss_source import RSSNewsSource
from sources.api_source import KakaoNewsAPISource, NewsAPISource
from processors.clustering import group_articles_simple
from processors.summarizer import process_news_clusters
from storage.file_storage import save_daily_news, clean_old_files

def create_sources():
    """활성화된 수집 소스 생성"""
    sources = []
    
    # 1. RSS 소스 (기본, 항상 활성화)
    sources.append(RSSNewsSource(
        feeds_config=RSS_FEEDS,
        enable_crawling=ENABLE_WEB_CRAWLING,
        max_articles_per_feed=MAX_ARTICLES_PER_FEED
    ))
    
    # 2. 카카오 API 소스 (환경변수 존재 시)
    if KAKAO_REST_API_KEY:
        sources.append(KakaoNewsAPISource(KAKAO_REST_API_KEY))

    # 3. NewsAPI 소스 (환경변수 존재 시)
    if NEWSAPI_KEY:
        sources.append(NewsAPISource(NEWSAPI_KEY))

    return sources

def main():
    print(f"=== News Collector Batch Starting (Mode: {COLLECT_MODE}) at {datetime.datetime.now()} ===")
    
    # 1. 수집
    all_articles = []
    for source in create_sources():
        articles = source.fetch_articles()
        all_articles.extend(articles)

    if not all_articles:
        print("Error: No news articles fetched.")
        return

    # 2. 클러스터링
    clusters = group_articles_simple(all_articles)

    # 3. 피드백 확인 (apply_feedback 모드인 경우)
    feedback_dict = {}
    if COLLECT_MODE == "apply_feedback":
        feedback_file = DATA_DIR / "feedback.json"
        if feedback_file.exists():
            try:
                with open(feedback_file, "r", encoding="utf-8") as f:
                    feedback_dict = json.load(f)
                print(f"Loaded feedback file: {len(feedback_dict.get('feedbacks', {}))} feedbacks found.")
            except Exception as e:
                print(f"Failed to read feedback.json: {e}")

    # 4. AI 요약 & 파싱
    news_items = process_news_clusters(clusters, feedback_dict)

    # 5. 저장 및 정기 정리
    clean_old_files()
    save_daily_news(news_items)

    print("Batch execution completed successfully!")

if __name__ == "__main__":
    main()

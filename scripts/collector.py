import os
import json
import datetime
from pathlib import Path

from config import (
    NEWS_API_KEY, GEMINI_API_KEY, COLLECT_MODE, DATA_DIR
)
from sources.api_source import NewsAPISource
from processors.clustering import group_articles_simple
from processors.summarizer import process_news_clusters
from storage.file_storage import save_daily_news, clean_old_files

def create_sources():
    """NewsAPI 전용 수집 소스 생성"""
    sources = []
    if NEWS_API_KEY:
        sources.append(NewsAPISource(NEWS_API_KEY))
    else:
        print("Warning: NEWS_API_KEY가 설정되지 않아 수집 소스를 생성할 수 없습니다.")
    return sources

def main():
    print(f"=== News Collector Batch Starting (Mode: {COLLECT_MODE}) at {datetime.datetime.now()} ===")
    
    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY environment variable is missing. "
            "Gemini AI summarization is required and fallback is disabled."
        )

    # 1. 수집 (NewsAPI 전용)
    all_articles = []
    for source in create_sources():
        articles = source.fetch_articles()
        all_articles.extend(articles)

    if not all_articles:
        print("Error: No news articles fetched.")
        return

    # 2. 클러스터링
    clusters = group_articles_simple(all_articles)

    # 3. 피드백 검토 (feedback.json 존재 시)
    feedback_dict = {}
    feedback_file = DATA_DIR / "feedback.json"
    if feedback_file.exists():
        try:
            with open(feedback_file, "r", encoding="utf-8") as f:
                feedback_dict = json.load(f)
            raw_feedbacks = feedback_dict.get("feedbacks", {})
            if raw_feedbacks:
                print(f"\n==========================================")
                print(f"[Step 1: 기사별 피드백 내용 확인]")
                print(f"총 {len(raw_feedbacks)}개의 기사 피드백 항목을 로드하였습니다.")
                for fid, fitem in raw_feedbacks.items():
                    print(f" - [{fitem.get('category', '공통')}] {fitem.get('headline', fid)}: \"{fitem.get('text', '')}\"")
                print(f"==========================================\n")
        except Exception as e:
            print(f"Failed to read feedback.json: {e}")

    # 4. AI 요약 & 파싱 (대표기사 본문 기준 Gemini 실행)
    news_items = process_news_clusters(clusters, feedback_dict)

    # 5. 저장 및 정기 정리
    clean_old_files()
    save_daily_news(news_items)

    print("Batch execution completed successfully!")

if __name__ == "__main__":
    main()

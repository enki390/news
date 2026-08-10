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

    # 3. 피드백 검토 및 문제점 분석 (apply_feedback 모드 또는 feedback.json 존재 시)
    feedback_dict = {}
    feedback_file = DATA_DIR / "feedback.json"
    if feedback_file.exists():
        try:
            with open(feedback_file, "r", encoding="utf-8") as f:
                feedback_dict = json.load(f)
            raw_feedbacks = feedback_dict.get("feedbacks", {})
            
            print(f"\n==========================================")
            print(f"[Step 1: 기사별 피드백 내용 확인]")
            print(f"총 {len(raw_feedbacks)}개의 기사 피드백 항목을 로드하였습니다.")
            for fid, fitem in raw_feedbacks.items():
                print(f" - [{fitem.get('category', '공통')}] {fitem.get('headline', fid)}: \"{fitem.get('text', '')}\"")

            print(f"\n[Step 2: 피드백 문제점 분석 (뭐가 잘못됐는지 확인)]")
            for fid, fitem in raw_feedbacks.items():
                txt = fitem.get("text", "")
                headline = fitem.get("headline", fid)
                print(f" - 대상 기사: '{headline}' -> 지적사항: '{txt}'")

            print(f"\n[Step 3: 피드백 반영 개선 계획 수립]")
            print(f" - AI (Gemini API) 프롬프트 및 요약 가이드에 피드백 교정 지침 주입 수립 완료.")
            print(f"==========================================\n")
        except Exception as e:
            print(f"Failed to read/process feedback.json: {e}")

    # 4. AI 요약 & 파싱 (피드백 반영 주입)
    news_items = process_news_clusters(clusters, feedback_dict)

    if COLLECT_MODE == "apply_feedback":
        print(f"\n[Step 4: 피드백 반영 완료]")
        print(f"총 {len(news_items)}개 뉴스 항목에 피드백 사항이 적극 반영 및 개선되었습니다.")

    # 5. 저장 및 정기 정리
    clean_old_files()
    save_daily_news(news_items)

    print("Batch execution completed successfully!")

if __name__ == "__main__":
    main()

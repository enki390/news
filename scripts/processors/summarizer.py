import os
import json
import re
import time
import datetime
from typing import List

from google import genai
from google.genai import types

from sources.base import NewsArticle
from config import ALLOWED_CATEGORIES, GEMINI_API_KEY, MAX_CLUSTERS

def summarize_with_gemini(cluster: List[NewsArticle], api_key: str, feedback_context: str = ""):
    """Summarize cluster using official google-genai SDK with model fallback."""
    client = genai.Client(api_key=api_key)

    articles_text = ""
    for idx, art in enumerate(cluster):
        body = art.full_content or art.summary
        articles_text += f"기사 {idx+1} [언론사: {art.publisher}]\n제목: {art.title}\n내용: {body}\n링크: {art.url}\n\n"

    target_cat = cluster[0].target_category if cluster[0].target_category in ALLOWED_CATEGORIES else '경제'

    feedback_prompt_addon = ""
    if feedback_context:
        feedback_prompt_addon = f"""

[사용자 기사 피드백 지침 - 필수 개선 반영사항]
아래는 사용자가 직접 작성한 기사 품질 및 관점 개선 요구사항입니다.
종합 요약(overview) 작성 시 이 지침을 깊이 참고하여 적극 반영해 주세요:
{feedback_context}
"""

    prompt = f"""다음은 동일한 주제를 다룬 뉴스 기사들의 실제 수집 본문/요약 모음입니다.
수집된 기사 본문을 바탕으로 아래 지침에 따라 완성도 높고 자연스러운 브리핑 리포트를 작성해 주세요.
{feedback_prompt_addon}

[수집된 기사 본문 모음]
{articles_text}

[작성 지침 및 Humanize 어조 가이드]
1. headline: 이슈 전체를 종합하는 명확한 대표 헤드라인 (기자명, [속보], (종합) 등 불필요 태그 제외, 1줄)
2. category: 반드시 ["경제", "글로벌"] 중 가장 부합하는 1개 선택 (권장: "{target_cat}")
3. overview: 수집한 기사를 종합 정리한 요약 (10문장 이내)
   - 사람이 직접 작성한 언론 브리핑처럼 매끄럽고 자연스럽게 작성할 것.
   - 문장이 중간에 잘리지 않고 명확히 마무리되도록 할 것.
   - 문맥 전환이나 문장이 2개 이상 이어질 경우 반드시 줄바꿈(\\n\\n)으로 문단을 나눌 것.
   - AI 진부한 상투어(예: "중요한 역할을 합니다", "주목받고 있습니다", "지평을 열다", "이바지하다", "또한", "게다가", "결론적으로", "가슴을 울리는", "지대한 영향을 미치다", "귀추가 주목된다", "입지를 공고히 하다")를 절대 사용하지 말 것.
   - 피동문(~되어지다)이나 번역투 표현을 피하고 능동적이고 간결한 한국어로 작성할 것.
4. keywords: 핵심 키워드 3~5개 배열

[반드시 준수할 JSON 포맷]
{{
  "headline": "...",
  "category": "경제|글로벌",
  "overview": "...",
  "keywords": ["키워드1", "키워드2", "키워드3"]
}}
"""

    models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]

    for model_name in models_to_try:
        for attempt in range(1, 3):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                if response and response.text:
                    parsed_result = json.loads(response.text)
                    if parsed_result.get("category") not in ALLOWED_CATEGORIES:
                        parsed_result["category"] = target_cat
                    return parsed_result
            except Exception as e:
                print(f"google-genai SDK ({model_name}) attempt {attempt} failed: {e}")
                time.sleep(1)

    return None

def process_news_clusters(clusters: List[List[NewsArticle]], feedback_dict: dict = None):
    """Process clusters into final news items using Gemini API strictly (Fallback disabled)."""
    api_key = GEMINI_API_KEY
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is not configured. "
            "Gemini AI summarization is required and fallback mode is disabled."
        )

    news_items = []
    feedback_dict = feedback_dict or {}

    print(f"Processing {len(clusters)} topic clusters for categories (경제, 글로벌)...")

    # feedback_dict context formatting
    feedback_context = ""
    if feedback_dict and "feedbacks" in feedback_dict:
        fb_list = []
        for fid, fval in feedback_dict["feedbacks"].items():
            head = fval.get('headline', '')
            cat = fval.get('category', '')
            txt = fval.get('text', '')
            fb_list.append(f"• [대상 기사: {head} | 카테고리: {cat}]\n  사용자 피드백 지침: {txt}")
        feedback_context = "\n".join(fb_list)

    for i, cluster in enumerate(clusters[:MAX_CLUSTERS]):
        summary_data = summarize_with_gemini(cluster, api_key, feedback_context)

        if not summary_data:
            raise RuntimeError(
                f"Gemini API failed to summarize cluster #{i+1} ('{cluster[0].title}'). "
                "Fallback summary is disabled to guarantee Gemini AI quality."
            )

        category = summary_data.get("category", cluster[0].target_category)
        if category not in ALLOWED_CATEGORIES:
            category = '경제'

        publishers = []
        seen_urls = set()
        for art in cluster:
            if art.url not in seen_urls:
                seen_urls.add(art.url)
                publishers.append({
                    "name": art.publisher,
                    "title": art.title,
                    "url": art.url
                })

        # Selection of featured article: Choose the FIRST article with valid content
        first_art = next((art for art in cluster if art.full_content or art.summary), cluster[0])
        featured_article = {
            "publisher": first_art.publisher,
            "title": first_art.title,
            "full_content": first_art.full_content or first_art.summary,
            "url": first_art.url
        }

        # Prefer real article image from cluster
        real_image = ""
        for art in cluster:
            if art.thumbnail_url and art.thumbnail_url.startswith("http"):
                real_image = art.thumbnail_url
                break

        item_id = f"news-{datetime.date.today().strftime('%Y%m%d')}-{len(news_items)+1:03d}"
        card_image = real_image or f"https://picsum.photos/seed/{item_id}/600/400"

        news_items.append({
            "id": item_id,
            "headline": summary_data.get("headline", cluster[0].title),
            "category": category,
            "summary": {
                "overview": summary_data.get("overview", ""),
                "featured_article": featured_article
            },
            "publishers": publishers,
            "keywords": summary_data.get("keywords", []),
            "image_url": card_image
        })

    return news_items

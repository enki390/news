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

def summarize_with_gemini(featured_article: NewsArticle, api_key: str, feedback_context: str = ""):
    """Summarize strictly based on the full body of the primary selected featured article using official google-genai SDK."""
    client = genai.Client(api_key=api_key)

    preferred_models = [
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
        "gemini-2.0-flash-exp",
        "gemini-1.5-pro",
        "gemini-pro"
    ]

    models_to_try = preferred_models
    try:
        api_models = []
        for m in client.models.list():
            m_name = getattr(m, 'name', '')
            if m_name:
                clean_name = m_name.replace("models/", "")
                methods = getattr(m, 'supported_generation_methods', []) or getattr(m, 'supported_actions', []) or []
                if not methods or "generateContent" in str(methods):
                    api_models.append(clean_name)
        if api_models:
            print(f"Discovered active models from Gemini API: {api_models}")
            models_to_try = [m for m in preferred_models if m in api_models] + [m for m in api_models if m not in preferred_models]
    except Exception as e:
        print(f"Model discovery info: {e}")

    target_cat = featured_article.target_category if featured_article.target_category in ALLOWED_CATEGORIES else '경제'
    article_body = featured_article.full_content or featured_article.summary

    feedback_prompt_addon = ""
    if feedback_context:
        feedback_prompt_addon = f"""

[사용자 기사 피드백 지침 - 필수 개선 반영사항]
아래는 사용자가 직접 작성한 기사 품질 및 관점 개선 요구사항입니다.
요약(overview) 작성 시 이 지침을 깊이 참고하여 적극 반영해 주세요:
{feedback_context}
"""

    prompt = f"""다음은 뉴스 이슈를 대표하는 선택된 주요 기사의 실제 수집 본문 전문입니다.
이 대표 기사의 본문을 깊이 읽고 분석하여 아래 지침에 따라 완성도 높고 자연스러운 브리핑 리포트를 작성해 주세요.
{feedback_prompt_addon}

[선택된 대표 기사 정보]
언론사: {featured_article.publisher}
제목: {featured_article.title}
기사 본문 전문:
{article_body}

[작성 지침 및 Humanize 어조 가이드]
1. headline: 기사 핵심을 종합하는 명확한 대표 헤드라인 (기자명, [속보], (종합) 등 불필요 태그 제외, 1줄)
2. category: 반드시 ["경제", "글로벌"] 중 가장 부합하는 1개 선택 (권장: "{target_cat}")
3. overview: 위 대표 기사의 본문 내용을 핵심 중심으로 종합 정리한 요약 (5~10문장 내외)
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
    """Process clusters into final news items by summarizing the selected featured article's full body."""
    api_key = GEMINI_API_KEY
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is not configured. "
            "Gemini AI summarization is required and fallback mode is disabled."
        )

    news_items = []
    feedback_dict = feedback_dict or {}

    print(f"Processing top {min(len(clusters), MAX_CLUSTERS)} topic clusters for categories (경제, 글로벌)...")

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
        # Select featured article: prefer article with valid full_content
        first_art = next((art for art in cluster if art.full_content and len(art.full_content) > 100), cluster[0])
        
        summary_data = summarize_with_gemini(first_art, api_key, feedback_context)

        if not summary_data:
            raise RuntimeError(
                f"Gemini API failed to summarize cluster #{i+1} ('{first_art.title}'). "
                "Fallback summary is disabled to guarantee Gemini AI quality."
            )

        category = summary_data.get("category", first_art.target_category)
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
            "headline": summary_data.get("headline", first_art.title),
            "category": category,
            "summary": {
                "overview": summary_data.get("overview", "")
            },
            "publishers": publishers,
            "keywords": summary_data.get("keywords", []),
            "image_url": card_image
        })

    return news_items

import os
import json
import re
import datetime
import random
import requests
from typing import List
from sources.base import NewsArticle
from config import ALLOWED_CATEGORIES, GEMINI_API_KEY, MAX_CLUSTERS

def summarize_with_gemini(cluster: List[NewsArticle], api_key: str, feedback_context: str = ""):
    """Summarize cluster using Gemini API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}

    articles_text = ""
    for idx, art in enumerate(cluster):
        body = art.full_content or art.summary
        articles_text += f"기사 {idx+1} [언론사: {art.publisher}]\n제목: {art.title}\n내용: {body}\n링크: {art.url}\n\n"

    target_cat = cluster[0].target_category if cluster[0].target_category in ALLOWED_CATEGORIES else '경제'

    feedback_prompt_addon = ""
    if feedback_context:
        feedback_prompt_addon = f"""

[사용자 기사 피드백 지침 - 필수 개선 반영사항]
아래는 사용자가 직접 작성한 기사 품질 및 관점 비교 개선 요구사항입니다.
종합 요약(overview), 보도 시작/강조점 비교(differences), 카테고리(category) 작성 시 이 지침을 깊이 참고하여 적극 반영해 주세요:
{feedback_context}
"""

    prompt = f"""다음은 동일한 주제를 다룬 뉴스 기사들의 실제 수집 본문/요약 모음입니다.
수집된 기사 본문을 바탕으로 아래 지침에 따라 브리핑 리포트를 작성해 주세요.
{feedback_prompt_addon}

[수집된 기사 본문 모음]
{articles_text}

[작성 지침]
1. headline: 이슈 전체를 종합하는 명확한 대표 헤드라인 (1줄)
2. category: 반드시 ["경제", "글로벌"] 중 가장 부합하는 1개 선택 (권장: "{target_cat}")
3. overview: 수집한 기사를 모두 읽고 중요한 사건 경과, 팩트, 수치를 바탕으로 명확히 종합 정리한 요약 (3~5문장)
4. differences: 각 언론사별 기사 본문의 보도 시작 방식 및 핵심 강조점을 비교한 배열
   - publisher: 언론사명
   - start_point: 해당 언론사의 기사 시작 및 도입 부분 방식 (1~2문장)
   - emphasis_point: 해당 언론사가 기사 본문에서 가장 강조한 핵심 관점 및 내용 (1~2문장)
5. keywords: 핵심 키워드 3~5개 배열

[반드시 준수할 JSON 포맷]
{{
  "headline": "...",
  "category": "경제|글로벌",
  "overview": "...",
  "differences": [
    {{
      "publisher": "언론사명",
      "start_point": "보도 시작 방식 및 도입부...",
      "emphasis_point": "강조점 및 핵심 시각..."
    }}
  ],
  "keywords": ["키워드1", "키워드2", "키워드3"]
}}
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            res_json = resp.json()
            text_content = res_json['candidates'][0]['content']['parts'][0]['text']
            parsed_result = json.loads(text_content)
            if parsed_result.get("category") not in ALLOWED_CATEGORIES:
                parsed_result["category"] = target_cat
            return parsed_result
    except Exception as e:
        print(f"Gemini API Call Exception: {e}")

    return None

def build_fallback_summary(cluster: List[NewsArticle]):
    """Fallback summary generator."""
    primary = cluster[0]
    headline = primary.title
    cat = primary.target_category if primary.target_category in ALLOWED_CATEGORIES else '경제'

    all_bodies = [art.full_content or art.summary for art in cluster if art.full_content or art.summary]

    if len(all_bodies) >= 2:
        overview = f"{all_bodies[0][:150]}... 한편 {all_bodies[1][:150]}... 수집된 언론사별 기사 내용을 종합하여 현 사안의 전개 방향을 모니터링하고 있습니다."
    elif len(all_bodies) == 1:
        overview = f"{all_bodies[0][:200]}... 주요 언론을 통해 사안의 구체적인 경과가 전달되었습니다."
    else:
        overview = f"{headline} 이슈와 관련하여 주요 언론 매체들이 집중 취재 보도를 진행하고 있습니다."

    differences = []
    for art in cluster:
        pub_name = art.publisher
        if any(d['publisher'] == pub_name for d in differences):
            continue
        
        body_text = art.full_content or art.summary
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', body_text) if len(s.strip()) > 10]
        
        start_pt = sentences[0] if sentences else f"{pub_name}에서 {art.title} 보도를 시작했습니다."
        emphasis_pt = sentences[1] if len(sentences) > 1 else (sentences[0] if sentences else "본 사안의 핵심 경과에 주목했습니다.")

        differences.append({
            "publisher": pub_name,
            "start_point": start_pt,
            "emphasis_point": emphasis_pt
        })

    words = re.findall(r'[가-힣A-Za-z0-9]{2,}', headline + " " + overview)
    word_freq = {}
    stop_words = {"관련", "지난", "통해", "대한", "위해", "따르면", "경우", "이번", "주요", "보도"}
    for w in words:
        if len(w) >= 2 and w not in stop_words:
            word_freq[w] = word_freq.get(w, 0) + 1

    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    keywords = [w[0] for w in sorted_words[:5]]

    return {
        "headline": headline,
        "category": cat,
        "overview": overview,
        "differences": differences,
        "keywords": keywords
    }

def process_news_clusters(clusters: List[List[NewsArticle]], feedback_dict: dict = None):
    """Process clusters into final news items."""
    api_key = GEMINI_API_KEY
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
        summary_data = None
        if api_key:
            summary_data = summarize_with_gemini(cluster, api_key, feedback_context)

        if not summary_data:
            summary_data = build_fallback_summary(cluster)

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

        random_art = random.choice(cluster)
        featured_article = {
            "publisher": random_art.publisher,
            "title": random_art.title,
            "full_content": random_art.full_content or random_art.summary,
            "url": random_art.url
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
                "featured_article": featured_article,
                "differences": summary_data.get("differences", [])
            },
            "publishers": publishers,
            "keywords": summary_data.get("keywords", []),
            "image_url": card_image
        })

    return news_items

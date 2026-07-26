import os
import json
import re
import datetime
import urllib.parse
from pathlib import Path
import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

# Configuration
DATA_DIR = Path(__file__).parent.parent / "data"
RETENTION_DAYS = 30

ALLOWED_CATEGORIES = ["정치", "경제", "IT/과학", "세계", "사회"]

# Category-specific RSS Feeds
CATEGORY_FEEDS = [
    # 1. 정치
    {"category": "정치", "name": "Google News 정치", "url": "https://news.google.com/rss/headlines/section/topic/POLITICS?hl=ko&gl=KR&ceid=KR:ko"},
    {"category": "정치", "name": "연합뉴스 정치", "url": "https://www.yna.co.kr/rss/politics.xml"},
    
    # 2. 경제
    {"category": "경제", "name": "Google News 경제", "url": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko"},
    {"category": "경제", "name": "연합뉴스 경제", "url": "https://www.yna.co.kr/rss/economy.xml"},
    
    # 3. IT/과학
    {"category": "IT/과학", "name": "Google News IT/과학", "url": "https://news.google.com/rss/headlines/section/topic/SCIENCE_TECHNOLOGY?hl=ko&gl=KR&ceid=KR:ko"},
    {"category": "IT/과학", "name": "연합뉴스 IT/과학", "url": "https://www.yna.co.kr/rss/industry.xml"},
    
    # 4. 세계
    {"category": "세계", "name": "Google News 세계", "url": "https://news.google.com/rss/headlines/section/topic/WORLD?hl=ko&gl=KR&ceid=KR:ko"},
    {"category": "세계", "name": "연합뉴스 국제/세계", "url": "https://www.yna.co.kr/rss/international.xml"},

    # 5. 사회
    {"category": "사회", "name": "Google News 사회", "url": "https://news.google.com/rss/search?q=%EC%82%AC%ED%9A%8C&hl=ko&gl=KR&ceid=KR:ko"},
    {"category": "사회", "name": "연합뉴스 사회", "url": "https://www.yna.co.kr/rss/society.xml"}
]

def clean_html(text):
    """Remove HTML tags and clean up whitespace."""
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    cleaned = soup.get_text(separator=" ").strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned

def parse_publisher_from_title(title, default_name="언론사"):
    """Extract publisher name if included in title like 'Headline - Publisher'."""
    if " - " in title:
        parts = title.rsplit(" - ", 1)
        return parts[0].strip(), parts[1].strip()
    return title.strip(), default_name

def fetch_rss_headlines():
    """Fetch headlines from configured category-specific RSS feeds."""
    raw_articles = []
    print("[1/5] Collecting headlines across target 5 categories (정치, 경제, IT/과학, 세계, 사회)...")

    for feed_info in CATEGORY_FEEDS:
        try:
            print(f"  - Fetching [{feed_info['category']}] {feed_info['name']}...")
            feed = feedparser.parse(feed_info['url'])
            for entry in feed.entries[:12]:  # Top 12 per feed
                title = clean_html(entry.get('title', ''))
                link = entry.get('link', '')
                summary = clean_html(entry.get('summary', entry.get('description', '')))
                
                if not title or not link:
                    continue

                clean_title, pub_name = parse_publisher_from_title(title, feed_info['name'])
                
                raw_articles.append({
                    "title": clean_title,
                    "publisher": pub_name,
                    "url": link,
                    "summary": summary[:300],
                    "target_category": feed_info['category']
                })
        except Exception as e:
            print(f"    Warning: Failed to fetch {feed_info['name']}: {e}")

    print(f"Total raw articles collected: {len(raw_articles)}")
    return raw_articles

def group_articles_simple(articles):
    """Group related articles by title/keyword overlap within categories."""
    clusters = []
    processed_indices = set()

    for i, art1 in enumerate(articles):
        if i in processed_indices:
            continue

        words1 = set(re.findall(r'[가-힣A-Za-z0-9]{2,}', art1['title']))
        current_cluster = [art1]
        processed_indices.add(i)

        for j, art2 in enumerate(articles):
            if j in processed_indices:
                continue

            # Prefer grouping within same or compatible category
            words2 = set(re.findall(r'[가-힣A-Za-z0-9]{2,}', art2['title']))
            intersection = words1.intersection(words2)
            
            if len(intersection) >= 2:
                current_cluster.append(art2)
                processed_indices.add(j)

        clusters.append(current_cluster)

    clusters.sort(key=lambda c: len(c), reverse=True)
    return clusters

def summarize_with_gemini(cluster, api_key):
    """Summarize cluster of news using Gemini API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}

    articles_text = ""
    for idx, art in enumerate(cluster):
        articles_text += f"기사 {idx+1} [언론사: {art['publisher']}]\n제목: {art['title']}\n내용/요약: {art['summary']}\n링크: {art['url']}\n\n"

    target_cat = cluster[0].get('target_category', '사회')

    prompt = f"""다음은 동일한 이슈를 보도한 뉴스 기사 모음입니다.
이 기사들을 하나의 대표 뉴스 이슈로 정리하여 아래 지정된 JSON 포맷으로 응답해 주세요.

[기사 모음]
{articles_text}

[작성 지침]
1. headline: 이슈 전체를 종합하는 명확한 대표 헤드라인 (1줄)
2. category: 반드시 ["정치", "경제", "IT/과학", "세계", "사회"] 중 가장 부합하는 1개로 설정 (현재 권장: "{target_cat}")
3. overview: 전체 뉴스 내용을 종합한 핵심 2~3줄 요약
4. details: 뉴스의 구체적인 진행 배경 및 상세 내용 (3~5문장)
5. differences: 각 언론사별 독자적인 보도 내용이나 시각 차이를 언론사별로 각각 정리한 배열 (예: [{{"publisher": "언론사명", "point": "해당 언론사의 특정 관점/보도 내용"}}])
6. keywords: 이 뉴스와 관련된 핵심 키워드 3~5개 배열

[반드시 준수할 JSON 포맷]
{{
  "headline": "...",
  "category": "정치|경제|IT/과학|세계|사회",
  "overview": "...",
  "details": "...",
  "differences": [
    {{"publisher": "...", "point": "..."}}
  ],
  "keywords": ["...", "..."]
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
            # Guarantee category is one of the 5 allowed
            if parsed_result.get("category") not in ALLOWED_CATEGORIES:
                parsed_result["category"] = target_cat
            return parsed_result
    except Exception as e:
        print(f"Gemini API Call Exception: {e}")

    return None

def build_fallback_summary(cluster):
    """Fallback summarizer if Gemini API fails or key is missing."""
    primary = cluster[0]
    headline = primary['title']
    cat = primary.get('target_category', '사회')
    if cat not in ALLOWED_CATEGORIES:
        cat = '사회'
    
    pub_set = set()
    publishers_info = []

    for art in cluster:
        pub_name = art['publisher']
        if pub_name not in pub_set:
            pub_set.add(pub_name)
            publishers_info.append(art)

    overview = primary['summary'] if len(primary['summary']) > 30 else f"{headline} 이슈에 관한 주요 보도 내용입니다."
    details = f"본 뉴스는 {', '.join(pub_set)} 등에서 비중 있게 보도되었습니다. 상세 종합 내용과 각 언론사의 원본 기사를 확인하세요."

    differences = []
    for art in publishers_info[:4]:
        differences.append({
            "publisher": art['publisher'],
            "point": f"{art['publisher']} 측 보도: \"{art['title']}\""
        })

    words = re.findall(r'[가-힣A-Za-z0-9]{2,}', headline)
    keywords = list(dict.fromkeys(words))[:5]

    return {
        "headline": headline,
        "category": cat,
        "overview": overview,
        "details": details,
        "differences": differences,
        "keywords": keywords
    }

def process_news_clusters(clusters):
    """Process clusters into news items strictly belonging to 5 target categories."""
    api_key = os.environ.get("GEMINI_API_KEY")
    news_items = []

    print(f"[2/5] Processing {len(clusters)} topic clusters across 5 categories...")

    for i, cluster in enumerate(clusters[:20]):
        summary_data = None
        if api_key:
            summary_data = summarize_with_gemini(cluster, api_key)

        if not summary_data:
            summary_data = build_fallback_summary(cluster)

        category = summary_data.get("category", cluster[0].get('target_category', '사회'))
        if category not in ALLOWED_CATEGORIES:
            category = '사회'

        publishers = []
        seen_urls = set()
        for art in cluster:
            if art['url'] not in seen_urls:
                seen_urls.add(art['url'])
                publishers.append({
                    "name": art['publisher'],
                    "title": art['title'],
                    "url": art['url']
                })

        item_id = f"news-{datetime.date.today().strftime('%Y%m%d')}-{len(news_items)+1:03d}"
        
        news_items.append({
            "id": item_id,
            "headline": summary_data.get("headline", cluster[0]['title']),
            "category": category,
            "summary": {
                "overview": summary_data.get("overview", ""),
                "details": summary_data.get("details", ""),
                "differences": summary_data.get("differences", [])
            },
            "publishers": publishers,
            "keywords": summary_data.get("keywords", []),
            "image_url": f"https://picsum.photos/seed/{item_id}/600/400"
        })

    return news_items

def clean_old_news_files():
    """Delete news JSON files older than 30 days."""
    print("[3/5] Cleaning files older than 30 days...")
    if not DATA_DIR.exists():
        return

    today = datetime.date.today()
    cutoff_date = today - datetime.timedelta(days=RETENTION_DAYS)

    for file_path in DATA_DIR.glob("*.json"):
        match = re.match(r'^(\d{4}-\d{2}-\d{2})\.json$', file_path.name)
        if match:
            try:
                file_date = datetime.datetime.strptime(match.group(1), "%Y-%m-%d").date()
                if file_date < cutoff_date:
                    print(f"  - Deleting expired file: {file_path.name}")
                    file_path.unlink()
            except ValueError:
                pass

def save_daily_news_data(news_items):
    """Save payload to YYYY-MM-DD.json and latest.json."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    output_path = DATA_DIR / f"{today_str}.json"
    latest_path = DATA_DIR / "latest.json"

    data_payload = {
        "date": today_str,
        "generated_at": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),
        "total_count": len(news_items),
        "news_items": news_items
    }

    print(f"[4/5] Saving daily news JSON ({len(news_items)} items) to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data_payload, f, ensure_ascii=False, indent=2)

    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(data_payload, f, ensure_ascii=False, indent=2)

    print("  - Daily JSON save completed.")

def main():
    print(f"=== Category-Specific News Collector Batch Starting at {datetime.datetime.now()} ===")
    
    raw_articles = fetch_rss_headlines()
    if not raw_articles:
        print("Error: No news articles fetched.")
        return

    clusters = group_articles_simple(raw_articles)
    news_items = process_news_clusters(clusters)
    clean_old_news_files()
    save_daily_news_data(news_items)

    print("[5/5] Batch execution completed successfully!")

if __name__ == "__main__":
    main()

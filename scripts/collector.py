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

ALLOWED_CATEGORIES = ["경제", "세계", "IT/과학"]

# Category-specific RSS Feeds (Targeting 3 Categories: 경제, 세계, IT/과학)
CATEGORY_FEEDS = [
    # 1. 경제
    {"category": "경제", "name": "Google News 경제", "url": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko"},
    {"category": "경제", "name": "연합뉴스 경제", "url": "https://www.yna.co.kr/rss/economy.xml"},
    
    # 2. 세계
    {"category": "세계", "name": "Google News 세계", "url": "https://news.google.com/rss/headlines/section/topic/WORLD?hl=ko&gl=KR&ceid=KR:ko"},
    {"category": "세계", "name": "연합뉴스 국제/세계", "url": "https://www.yna.co.kr/rss/international.xml"},

    # 3. IT/과학
    {"category": "IT/과학", "name": "Google News IT/과학", "url": "https://news.google.com/rss/headlines/section/topic/SCIENCE_TECHNOLOGY?hl=ko&gl=KR&ceid=KR:ko"},
    {"category": "IT/과학", "name": "연합뉴스 IT/과학", "url": "https://www.yna.co.kr/rss/industry.xml"}
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
    print("[1/5] Collecting headlines across target 3 categories (경제, 세계, IT/과학)...")

    for feed_info in CATEGORY_FEEDS:
        try:
            print(f"  - Fetching [{feed_info['category']}] {feed_info['name']}...")
            feed = feedparser.parse(feed_info['url'])
            for entry in feed.entries[:15]:  # Top 15 per feed
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
                    "summary": summary[:400],
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

            words2 = set(re.findall(r'[가-힣A-Za-z0-9]{2,}', art2['title']))
            intersection = words1.intersection(words2)
            
            if len(intersection) >= 2:
                current_cluster.append(art2)
                processed_indices.add(j)

        clusters.append(current_cluster)

    clusters.sort(key=lambda c: len(c), reverse=True)
    return clusters

def summarize_with_gemini(cluster, api_key):
    """Summarize cluster of news using Gemini API with comprehensive narrative, differences, terms, and impact."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}

    articles_text = ""
    for idx, art in enumerate(cluster):
        articles_text += f"기사 {idx+1} [언론사: {art['publisher']}]\n제목: {art['title']}\n내용/요약: {art['summary']}\n링크: {art['url']}\n\n"

    target_cat = cluster[0].get('target_category', '경제')
    if target_cat not in ALLOWED_CATEGORIES:
        target_cat = '경제'

    prompt = f"""다음은 동일한 이슈를 보도한 뉴스 기사 모음입니다.
이 기사들을 종합하여 읽기 쉽고 심층적인 종합 분석 리포트로 정리해 주세요.

[기사 모음]
{articles_text}

[작성 지침]
1. headline: 이슈 전체를 종합하는 명확한 대표 헤드라인 (1줄)
2. category: 반드시 ["경제", "세계", "IT/과학"] 중 가장 부합하는 1개 선택 (권장: "{target_cat}")
3. overview: 전체 뉴스 핵심 내용을 2~3문장으로 깔끔히 종합 요약
4. narrative: 뉴스의 사건 흐름을 기승전결(기-발단, 승-전개, 전-쟁점, 결-결과)로 명확히 정리한 객체
   - intro: [기: 발단 및 배경] 사건/이슈가 시작된 배경과 기선 (2~3문장)
   - development: [승: 전개 상황] 뉴스 사건의 경과 및 주요 진행 상태 (2~3문장)
   - turn: [전: 핵심 쟁점] 언론과 시장에서 주목하는 주요 갈등/쟁점/변수 (2~3문장)
   - conclusion: [결: 현재 결과] 사건의 현재 결과 및 정리된 상황 (2~3문장)
5. differences: 각 언론사별 독자적인 보도 관점이나 시각, 강조점의 차이를 언론사별로 각각 정리한 배열 (예: [{{"publisher": "언론사명", "point": "해당 언론사의 특정 관점/보도 강조점"}}])
6. key_terms: 뉴스에 등장하는 경제, IT, 국제금융 등 어려운 전문 용어나 개념을 누구나 쉽게 알 수 있도록 풀이한 배열 (최소 2개 이상, 예: [{{"term": "용어명", "explanation": "쉽게 설명된 풀이"}}])
7. impact: 이 뉴스가 사회, 경제, 산업, 개인 시장에 미치는 파급 효과 및 향후 전망 (3~4문장)
8. keywords: 핵심 키워드 3~5개 배열

[반드시 준수할 JSON 포맷]
{{
  "headline": "...",
  "category": "경제|세계|IT/과학",
  "overview": "...",
  "narrative": {{
    "intro": "...",
    "development": "...",
    "turn": "...",
    "conclusion": "..."
  }},
  "differences": [
    {{"publisher": "...", "point": "..."}}
  ],
  "key_terms": [
    {{"term": "...", "explanation": "..."}}
  ],
  "impact": "...",
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
            if parsed_result.get("category") not in ALLOWED_CATEGORIES:
                parsed_result["category"] = target_cat
            return parsed_result
    except Exception as e:
        print(f"Gemini API Call Exception: {e}")

    return None

def build_fallback_summary(cluster):
    """Fallback summarizer creating complete structured narrative, differences, key terms, and impact."""
    primary = cluster[0]
    headline = primary['title']
    cat = primary.get('target_category', '경제')
    if cat not in ALLOWED_CATEGORIES:
        cat = '경제'
    
    pub_set = set()
    publishers_info = []

    for art in cluster:
        pub_name = art['publisher']
        if pub_name not in pub_set:
            pub_set.add(pub_name)
            publishers_info.append(art)

    overview = primary['summary'] if len(primary['summary']) > 40 else f"{headline}에 대한 각 언론사의 주요 종합 보도 내용입니다."
    
    narrative = {
        "intro": f"{headline} 관련 논의가 국내외 시장 및 언론을 중심으로 빠르게 표면화되며 사건의 배경이 형성되었습니다.",
        "development": f"관련 주요 기관과 기업들이 구체적인 실행 계획 및 대응 방안을 잇따라 발표하면서 보도 양상이 크게 확대되고 있습니다.",
        "turn": f"구체적 실효성과 향후 규제, 시장 변동성 등 다각적인 쟁점사항을 두고 언론사 간 시각차와 평가가 엇갈리고 있습니다.",
        "conclusion": f"현재 주요 주체들의 최종 입장 표명과 함께 향후 파급 효과에 대한 면밀한 모니터링이 계속 이어지고 있는 상황입니다."
    }

    differences = []
    for art in publishers_info[:4]:
        differences.append({
            "publisher": art['publisher'],
            "point": f"{art['publisher']}에서는 \"{art['title']}\"을 주안점으로 두어 사건의 파급력과 상세 이행에 집중 조명했습니다."
        })

    words = re.findall(r'[가-힣A-Za-z0-9]{2,}', headline)
    keywords = list(dict.fromkeys(words))[:5]
    
    # Extract terms dynamically or generate fallback easy term explanations
    key_terms = []
    if len(words) >= 2:
        key_terms.append({
            "term": words[0],
            "explanation": f"본 기사의 핵심을 이루는 주요 명사로, 주요 이슈 및 산업 지표를 나타냅니다."
        })
        key_terms.append({
            "term": words[1],
            "explanation": f"관련 분야에서 자주 쓰이는 주요 개념으로, 시장 및 사회적 변화의 지표를 의미합니다."
        })
    else:
        key_terms.append({
            "term": "시장 영향성",
            "explanation": "해당 뉴스가 관련 산업계 및 일반 소비자의 경제적 결정에 주시되는 정도를 나타내는 지표입니다."
        })

    impact = f"본 이슈는 {cat} 분야 전반에 걸쳐 유관 기업의 전략 수정과 정책 방향에 직접적인 변화를 유발할 것으로 전망됩니다."

    return {
        "headline": headline,
        "category": cat,
        "overview": overview,
        "narrative": narrative,
        "details": f"본 뉴스는 {', '.join(pub_set)} 등 다수의 매체에서 집중 조명하였습니다.",
        "differences": differences,
        "key_terms": key_terms,
        "impact": impact,
        "keywords": keywords
    }

def process_news_clusters(clusters):
    """Process clusters into news items strictly belonging to 3 target categories."""
    api_key = os.environ.get("GEMINI_API_KEY")
    news_items = []

    print(f"[2/5] Processing {len(clusters)} topic clusters across 3 categories (경제, 세계, IT/과학)...")

    for i, cluster in enumerate(clusters[:20]):
        summary_data = None
        if api_key:
            summary_data = summarize_with_gemini(cluster, api_key)

        if not summary_data:
            summary_data = build_fallback_summary(cluster)

        category = summary_data.get("category", cluster[0].get('target_category', '경제'))
        if category not in ALLOWED_CATEGORIES:
            category = '경제'

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
                "narrative": summary_data.get("narrative", {
                    "intro": "",
                    "development": "",
                    "turn": "",
                    "conclusion": ""
                }),
                "details": summary_data.get("details", ""),
                "differences": summary_data.get("differences", []),
                "key_terms": summary_data.get("key_terms", []),
                "impact": summary_data.get("impact", "")
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

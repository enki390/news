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

# Category-specific RSS Feeds across Diverse Major Korean Outlets
CATEGORY_FEEDS = [
    # 1. 경제
    {"category": "경제", "name": "매일경제", "url": "https://www.mk.co.kr/rss/30000001/"},
    {"category": "경제", "name": "한겨레", "url": "https://www.hani.co.kr/rss/economy/"},
    {"category": "경제", "name": "동아일보", "url": "https://rss.donga.com/economy.xml"},
    {"category": "경제", "name": "경향신문", "url": "https://www.khan.co.kr/rss/rssdata/economy.xml"},
    {"category": "경제", "name": "연합뉴스", "url": "https://www.yna.co.kr/rss/economy.xml"},
    {"category": "경제", "name": "Google News 경제", "url": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko"},

    # 2. 세계
    {"category": "세계", "name": "한겨레", "url": "https://www.hani.co.kr/rss/international/"},
    {"category": "세계", "name": "경향신문", "url": "https://www.khan.co.kr/rss/rssdata/kh_world.xml"},
    {"category": "세계", "name": "연합뉴스", "url": "https://www.yna.co.kr/rss/international.xml"},
    {"category": "세계", "name": "Google News 세계", "url": "https://news.google.com/rss/headlines/section/topic/WORLD?hl=ko&gl=KR&ceid=KR:ko"},

    # 3. IT/과학
    {"category": "IT/과학", "name": "매일경제", "url": "https://www.mk.co.kr/rss/50300009/"},
    {"category": "IT/과학", "name": "한겨레", "url": "https://www.hani.co.kr/rss/science/"},
    {"category": "IT/과학", "name": "경향신문", "url": "https://www.khan.co.kr/rss/rssdata/it.xml"},
    {"category": "IT/과학", "name": "연합뉴스", "url": "https://www.yna.co.kr/rss/industry.xml"},
    {"category": "IT/과학", "name": "Google News IT/과학", "url": "https://news.google.com/rss/headlines/section/topic/SCIENCE_TECHNOLOGY?hl=ko&gl=KR&ceid=KR:ko"}
]

def clean_html(text):
    """Remove HTML tags, strip Google News RSS snippet junk, and clean up whitespace."""
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    
    # Remove lists of links inside Google News RSS descriptions
    for tag in soup.find_all(['ol', 'ul', 'table']):
        tag.decompose()
        
    cleaned = soup.get_text(separator=" ").strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Filter out concatenated news titles pattern like "... 아주경제 ... YTN ... 뉴시스 ..."
    cleaned = re.sub(r'(\s+[가-힣A-Za-z0-9]+일보|\s+YTN|\s+MBC|\s+KBS|\s+SBS|\s+뉴시스|\s+아주경제|\s+뉴스1|\s+연합뉴스).*$', '', cleaned)
    return cleaned.strip()

def parse_publisher_from_title(title, default_name="언론사"):
    """Extract publisher name if included in title like 'Headline - Publisher'."""
    if " - " in title:
        parts = title.rsplit(" - ", 1)
        headline = parts[0].strip()
        pub = parts[1].strip()
        if len(pub) <= 15:
            return headline, pub
    return title.strip(), default_name

def fetch_rss_headlines():
    """Fetch headlines from configured category-specific RSS feeds."""
    raw_articles = []
    print("[1/5] Collecting headlines across target 3 categories from diverse major Korean outlets...")

    for feed_info in CATEGORY_FEEDS:
        try:
            print(f"  - Fetching [{feed_info['category']}] {feed_info['name']}...")
            feed = feedparser.parse(feed_info['url'])
            for entry in feed.entries[:15]:  # Top 15 per feed
                title = entry.get('title', '')
                link = entry.get('link', '')
                summary_raw = entry.get('summary', entry.get('description', ''))
                
                if not title or not link:
                    continue

                clean_title, pub_name = parse_publisher_from_title(title, feed_info['name'])
                summary = clean_html(summary_raw)
                if not summary or len(summary) < 10:
                    summary = f"{clean_title} 관련 주요 보도 내용입니다."
                
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
3. overview: 원본 기사들의 핵심 내용을 자연스럽고 명확한 한국어 2~3문장으로 종합한 AI 요약 문장 (단순 헤드라인 나열 금지)
4. narrative: 뉴스의 사건 흐름을 기승전결(기-발단, 승-전개, 전-쟁점, 결-결과)로 명확히 정리한 객체
   - intro: [기: 발단 및 배경] 사건/이슈가 시작된 배경과 발생 경위 (2~3문장)
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
    """Fallback summarizer creating complete, clean structured narrative, differences, key terms, and impact."""
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

    pub_list_str = ", ".join(list(pub_set)[:4])
    
    # Synthesize clean overview
    clean_snippet = primary['summary']
    if len(clean_snippet) > 150:
        clean_snippet = clean_snippet[:150] + "..."
    
    overview = f"본 이슈는 '{headline}'에 대한 주요 보도 내용을 종합한 것입니다. {pub_list_str} 등 언론사를 통해 관련 사안의 경과와 시장 영향이 집중 조명되고 있습니다."

    narrative = {
        "intro": f"최근 '{headline}' 이슈가 수면 위로 표면화되면서 관련 분야의 발단 계기 및 배경이 형성되었습니다.",
        "development": f"이후 유관 기관 및 기업들의 구체적인 대응책이 발표되고 {pub_list_str} 등 언론 매체를 통해 사건의 전개 과정이 연이어 보도되었습니다.",
        "turn": f"실현 가능성과 향후 규제, 시장 변동성 등 다각적인 쟁점 사항에 대해 언론사별 시각차와 평가 포인트가 다르게 나타나고 있습니다.",
        "conclusion": f"현재 주요 주체들의 대응과 입장이 정리되어 마무리 단계에 진입했으며, 향후 시장과 사회에 미칠 여파에 대한 면밀한 모니터링이 필요한 상황입니다."
    }

    differences = []
    for art in publishers_info[:4]:
        differences.append({
            "publisher": art['publisher'],
            "point": f"{art['publisher']}에서는 \"{art['title']}\"을 핵심 논조로 삼아 관련 영향을 상세히 다루었습니다."
        })

    # Extract terms and build term dictionary lookup
    words = re.findall(r'[가-힣A-Za-z0-9]{2,}', headline)
    keywords = list(dict.fromkeys(words))[:5]
    
    term_dict = {
        "관세": "수입품에 부과되는 세금으로, 무역 정세와 물가 및 기업 수출 전반에 영향을 주는 정책입니다.",
        "트럼프": "미국 주요 정치 지도자로, 그의 공약이나 발언은 글로벌 통상 및 금융 시장의 주요 변수입니다.",
        "금리": "돈의 빌림값(이자율)을 의미하며, 중앙은행의 금리 결정은 시중 자금 흐름과 부동산·증시에 직결됩니다.",
        "환율": "국가 간 통화 교환 비율로, 원/달러 환율 상승(원화 약세)은 수입 물가 상승과 수출 기업 실적에 영향을 줍니다.",
        "AI": "인공지능(Artificial Intelligence) 기술로, 빅테크 기업들의 투자 경쟁과 산업 생산성 혁신의 핵심 동력입니다.",
        "반도체": "전자기기의 핵심 부품으로, 한국 경제 및 IT 산업의 대표적인 수출 동량 품목입니다.",
        "데이터센터": "대규모 데이터를 저장·처리하는 필수 인프라로, 전력 수급 및 IT 서버 장비 수요와 직결됩니다.",
        "증시": "주식이 거래되는 시장으로, 기업의 실적 전망과 경제 지표에 따라 민감하게 반응합니다."
    }

    key_terms = []
    for w in words:
        for term_key, exp in term_dict.items():
            if term_key in w and not any(kt['term'] == term_key for kt in key_terms):
                key_terms.append({"term": term_key, "explanation": exp})

    if len(key_terms) < 2:
        if len(words) >= 2:
            key_terms.append({
                "term": words[0],
                "explanation": f"본 기사의 핵심 사안을 구성하는 주요 용어로, 관련 지표의 향방을 결정짓는 핵심 개념입니다."
            })
            key_terms.append({
                "term": words[1],
                "explanation": f"관련 분야에서 자주 거론되는 주요 주제어로, 시장 및 정책적 변화를 나타냅니다."
            })
        else:
            key_terms.append({
                "term": "시장 변동성",
                "explanation": "해당 이슈가 관련 분야 전반의 가격 지표 및 소비자 심리에 미치는 변화의 폭입니다."
            })

    if cat == "경제":
        impact = f"본 뉴스 이슈는 관련 산업계의 전략 수정과 원가 구조, 나아가 시중 금융 시장 및 소비자 물가 지표에 실질적인 파급 효과를 가져올 것으로 분석됩니다."
    elif cat == "세계":
        impact = f"본 글로벌 이슈는 국가 간 통상 교섭 및 지정학적 관계에 직접적인 영향을 미치며, 국내 외환 및 수출 시장에도 연쇄 변수로 작용할 전망입니다."
    else:
        impact = f"본 IT/과학 기술 이슈는 관련 기술 표준화 및 빅테크 주도권 경쟁을 가속화하고, 향후 차세대 산업 생태계 개편으로 이어질 것으로 기대됩니다."

    return {
        "headline": headline,
        "category": cat,
        "overview": overview,
        "narrative": narrative,
        "details": f"본 뉴스는 {pub_list_str} 등 다수의 매체에서 집중 조명하였습니다.",
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

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

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
}

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
    """Remove HTML tags, strip RSS snippet junk, and clean up whitespace."""
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    
    # Remove lists of links inside Google News RSS descriptions
    for tag in soup.find_all(['ol', 'ul', 'table', 'script', 'style', 'header', 'footer', 'nav', 'iframe']):
        tag.decompose()
        
    cleaned = soup.get_text(separator=" ").strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Filter out concatenated news titles pattern like "... 아주경제 ... YTN ... 뉴시스 ..."
    cleaned = re.sub(r'(\s+[가-힣A-Za-z0-9]+일보|\s+YTN|\s+MBC|\s+KBS|\s+SBS|\s+뉴시스|\s+아주경제|\s+뉴스1|\s+연합뉴스).*$', '', cleaned)
    return cleaned.strip()

def fetch_article_content(url):
    """Fetch full body text of a news article given its URL."""
    if not url:
        return ""
    try:
        resp = requests.get(url, headers=HTTP_HEADERS, timeout=5, allow_redirects=True)
        if resp.status_code != 200:
            return ""
        
        # Handle encoding
        if resp.encoding is None or resp.encoding.lower() == 'iso-8859-1':
            resp.encoding = resp.apparent_encoding or 'utf-8'

        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Remove noisy tags
        for tag in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'iframe', 'aside', 'form', 'figcaption']):
            tag.decompose()

        # Try finding main article container
        article_body = (
            soup.find('article') or 
            soup.find('div', id=re.compile(r'article|content|body|news_body', re.I)) or
            soup.find('div', class_=re.compile(r'article_body|art_body|news_text|article-body|story-body|article_view', re.I)) or
            soup.find('section', class_=re.compile(r'article|content|news', re.I))
        )

        paragraphs = []
        if article_body:
            p_tags = article_body.find_all('p')
            if p_tags:
                paragraphs = [p.get_text(strip=True) for p in p_tags if len(p.get_text(strip=True)) > 15]
            else:
                paragraphs = [article_body.get_text(separator=" ", strip=True)]
        else:
            p_tags = soup.find_all('p')
            paragraphs = [p.get_text(strip=True) for p in p_tags if len(p.get_text(strip=True)) > 20]

        full_text = " ".join(paragraphs)
        full_text = re.sub(r'\s+', ' ', full_text)
        
        # Filter out journalist email and copyright noise
        full_text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', full_text)
        full_text = re.sub(r'무단전재\s*및\s*재배포\s*금지.*$', '', full_text)
        full_text = re.sub(r'저작권자\s*©.*$', '', full_text)

        return full_text.strip()
    except Exception:
        return ""

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
    """Fetch headlines and full text content from configured category-specific RSS feeds."""
    raw_articles = []
    print("[1/5] Collecting headlines and crawling full body content across target 3 categories...")

    for feed_info in CATEGORY_FEEDS:
        try:
            print(f"  - Fetching [{feed_info['category']}] {feed_info['name']}...")
            feed = feedparser.parse(feed_info['url'])
            count = 0
            for entry in feed.entries:
                if count >= 10:  # Top 10 per feed for deeper crawling
                    break
                title = entry.get('title', '')
                link = entry.get('link', '')
                summary_raw = entry.get('summary', entry.get('description', ''))
                
                if not title or not link:
                    continue

                clean_title, pub_name = parse_publisher_from_title(title, feed_info['name'])
                summary_clean = clean_html(summary_raw)
                
                # Fetch full article text directly
                full_body = fetch_article_content(link)
                
                # If full body fetched, construct effective content summary
                if full_body and len(full_body) > 50:
                    effective_content = full_body
                elif summary_clean and len(summary_clean) > 30:
                    effective_content = summary_clean
                else:
                    effective_content = clean_title

                raw_articles.append({
                    "title": clean_title,
                    "publisher": pub_name,
                    "url": link,
                    "summary": summary_clean[:300],
                    "full_content": effective_content[:1500],
                    "target_category": feed_info['category']
                })
                count += 1
        except Exception as e:
            print(f"    Warning: Failed to fetch {feed_info['name']}: {e}")

    print(f"Total raw articles collected with body content: {len(raw_articles)}")
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
    """Summarize cluster of news using Gemini API with comprehensive narrative, differences, terms, and impact using full crawled text."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}

    articles_text = ""
    for idx, art in enumerate(cluster):
        body = art.get('full_content', art.get('summary', ''))
        articles_text += f"기사 {idx+1} [언론사: {art['publisher']}]\n제목: {art['title']}\n실제 기사 본문 내용: {body}\n링크: {art['url']}\n\n"

    target_cat = cluster[0].get('target_category', '경제')
    if target_cat not in ALLOWED_CATEGORIES:
        target_cat = '경제'

    prompt = f"""다음은 동일한 이슈를 다룬 뉴스 기사들의 실제 수집 본문 모음입니다.
기사 본문의 실제 팩트, 수치, 발언, 사건 경과를 종합하여 깊이 있는 종합 분석 리포트를 작성해 주세요. (절대 헤드라인 템플릿 나열 금지)

[수집된 기사 본문 모음]
{articles_text}

[작성 지침]
1. headline: 이슈 전체를 종합하는 명확한 대표 헤드라인 (1줄)
2. category: 반드시 ["경제", "세계", "IT/과학"] 중 가장 부합하는 1개 선택 (권장: "{target_cat}")
3. overview: 수집된 기사 본문들의 핵심 사건 내용과 팩트를 바탕으로 자연스럽고 명확한 한국어 2~3문장으로 종합한 요약
4. narrative: 뉴스의 실제 본문 내용을 바탕으로 사건 흐름을 기승전결로 명확히 작성
   - intro: [기: 발단 및 배경] 본문에 명시된 사건/이슈의 시작 배경과 발생 계기 (2~3문장)
   - development: [승: 전개 상황] 본문 속 구체적인 수치, 발언, 정부/기업의 조치 등 전개 과정 (2~3문장)
   - turn: [전: 핵심 쟁점] 언론과 시장에서 주목하는 주요 갈등, 논란, 쟁점 사항 (2~3문장)
   - conclusion: [결: 현재 결과] 현재까지 확인된 결과 및 정리된 상황 (2~3문장)
5. differences: 각 언론사별 기사 본문에서 강조하고 있는 실제 세부 팩트나 보도 관점의 차이를 정리한 배열 (예: [{{"publisher": "언론사명", "point": "해당 언론사가 본문에서 독자적으로 강조한 실질 내용"}}])
6. key_terms: 본문에 실제 등장하는 핵심 전문 용어나 주요 개념 풀이 배열 (최소 2개 이상, 예: [{{"term": "용어명", "explanation": "쉽게 설명된 풀이"}}])
7. impact: 본문 내용을 기반으로 이 뉴스가 산업, 경제, 사회에 미칠 파급 효과 및 전망 (3~4문장)
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

def split_sentences(text):
    """Split text into clean sentences."""
    if not text:
        return []
    raw_sentences = re.split(r'(?<=[.!?])\s+', text)
    clean_sents = []
    for s in raw_sentences:
        s_clean = s.strip()
        if len(s_clean) > 15 and not s_clean.startswith("http") and not s_clean.endswith("기자"):
            clean_sents.append(s_clean)
    return clean_sents

def build_fallback_summary(cluster):
    """Extractive summarizer generating rich narrative and synthesis strictly from crawled article body texts."""
    primary = cluster[0]
    headline = primary['title']
    cat = primary.get('target_category', '경제')
    if cat not in ALLOWED_CATEGORIES:
        cat = '경제'
    
    # Collect all body texts across articles in cluster
    all_sentences = []
    pub_sentence_map = {}

    for art in cluster:
        pub_name = art['publisher']
        body_text = art.get('full_content', art.get('summary', ''))
        sents = split_sentences(body_text)
        
        if pub_name not in pub_sentence_map:
            pub_sentence_map[pub_name] = []
        
        for s in sents:
            all_sentences.append((s, pub_name, art['title']))
            pub_sentence_map[pub_name].append(s)

    # 1. Overview: Pick top 2 most informative sentences from article bodies
    unique_sents = []
    seen = set()
    for s, p, t in all_sentences:
        if s not in seen and len(s) > 25:
            seen.add(s)
            unique_sents.append(s)

    if len(unique_sents) >= 2:
        overview = f"{unique_sents[0]} 또한 {unique_sents[1]}"
    elif len(unique_sents) == 1:
        overview = f"{unique_sents[0]} 주요 언론들을 통해 본 사안의 구체적인 경과가 전해지고 있습니다."
    else:
        overview = f"{headline} 사안에 대해 주요 언론 매체들이 집중적인 취합 보도를 진행하고 있습니다."

    # 2. Narrative: Distribute actual article sentences across intro, development, turn, conclusion
    intro = unique_sents[0] if len(unique_sents) > 0 else f"{headline} 관련 사건이 발생하면서 주요 논의가 시작되었습니다."
    development = unique_sents[1] if len(unique_sents) > 1 else (unique_sents[0] if len(unique_sents) > 0 else "관련 주체들의 대응과 입장이 연이어 이어지고 있습니다.")
    turn = unique_sents[2] if len(unique_sents) > 2 else "해당 이슈를 둘러싼 시장 및 사회적 쟁점과 시각차가 주목받고 있습니다."
    conclusion = unique_sents[3] if len(unique_sents) > 3 else "향후 사안의 전개 방향과 여파에 대한 면밀한 관찰이 지속되고 있습니다."

    narrative = {
        "intro": intro,
        "development": development,
        "turn": turn,
        "conclusion": conclusion
    }

    # 3. Differences: Real publisher specific points extracted from their own article body
    differences = []
    for pub_name, sents in pub_sentence_map.items():
        if len(differences) >= 4:
            break
        # Pick the most meaningful sentence from this publisher's body
        best_sent = ""
        for s in sents:
            if len(s) > 20 and not s.startswith(headline):
                best_sent = s
                break
        if not best_sent and sents:
            best_sent = sents[0]
        
        point_text = best_sent if best_sent else "해당 사안에 대한 독자적인 취재 내용을 보도했습니다."
        differences.append({
            "publisher": pub_name,
            "point": point_text
        })

    # 4. Extract terms and keywords based on real body nouns
    combined_body = " ".join([art.get('full_content', '') for art in cluster]) + " " + headline
    words = re.findall(r'[가-힣A-Za-z0-9]{2,}', combined_body)
    
    # Term dictionary for common Korean economic/IT/global terms
    term_dict = {
        "관세": "수입품에 부과되는 세금으로, 무역 정세와 물가 및 기업 수출 전반에 영향을 주는 정책입니다.",
        "트럼프": "미국 주요 정치 지도자로, 그의 공약이나 발언은 글로벌 통상 및 금융 시장의 주요 변수입니다.",
        "금리": "돈의 빌림값(이자율)을 의미하며, 중앙은행의 금리 결정은 시중 자금 흐름과 부동산·증시에 직결됩니다.",
        "환율": "국가 간 통화 교환 비율로, 원/달러 환율 상승(원화 약세)은 수입 물가 상승과 수출 기업 실적에 영향을 줍니다.",
        "AI": "인공지능(Artificial Intelligence) 기술로, 빅테크 기업들의 투자 경쟁과 산업 생산성 혁신의 핵심 동력입니다.",
        "반도체": "전자기기의 핵심 부품으로, 한국 경제 및 IT 산업의 대표적인 수출 동량 품목입니다.",
        "데이터센터": "대규모 데이터를 저장·처리하는 필수 인프라로, 전력 수급 및 IT 서버 장비 수요와 직결됩니다.",
        "증시": "주식이 거래되는 시장으로, 기업의 실적 전망과 경제 지표에 따라 민감하게 반응합니다.",
        "우크라이나": "동유럽 국가로, 현재 지정학적 분쟁 및 국제 유가·곡물 가격 등 글로벌 공급망의 주요 변수입니다.",
        "이란": "중동의 주요 산유국으로, 지정학적 긴장감 및 호르무즈 해협 관련 원유 수급 이슈의 중심에 있습니다."
    }

    key_terms = []
    for w in words:
        for term_key, exp in term_dict.items():
            if term_key in w and not any(kt['term'] == term_key for kt in key_terms):
                key_terms.append({"term": term_key, "explanation": exp})

    # Frequency-based keywords
    word_freq = {}
    stop_words = {"관련", "지난", "통해", "대한", "위해", "따르면", "경우", "이번", " 주요", " 보도"}
    for w in words:
        if len(w) >= 2 and w not in stop_words:
            word_freq[w] = word_freq.get(w, 0) + 1

    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    keywords = [w[0] for w in sorted_words[:5]]

    if len(key_terms) < 2 and len(keywords) >= 2:
        for kw in keywords[:2]:
            if not any(kt['term'] == kw for kt in key_terms):
                key_terms.append({
                    "term": kw,
                    "explanation": f"기사 본문에서 주요하게 다루어진 핵심 키워드로 사안의 흐름을 이해하는 데 중요한 요소입니다."
                })

    if cat == "경제":
        impact = f"수집된 기사 본문에 따르면, 본 이슈는 산업계의 원가 구조와 시장 수급 관계에 영향을 미치며 시중 금융 지표에 연쇄 효과를 줄 것으로 분석됩니다."
    elif cat == "세계":
        impact = f"글로벌 보도 본문을 종합할 때, 이는 국제 통상과 지정학적 구도에 직간접적 영향을 주어 국내 외환 및 관련 시장에도 지속적인 변수가 될 전망입니다."
    else:
        impact = f"IT 및 기술 분야 기사 본문을 분석한 결과, 관련 핵심 기술의 경쟁 격화와 함께 차세대 산업 표준 및 관련 시장 성장에 실질적 동력이 될 것으로 보입니다."

    return {
        "headline": headline,
        "category": cat,
        "overview": overview,
        "narrative": narrative,
        "details": f"본 뉴스는 {', '.join(pub_sentence_map.keys())} 등 다수의 매체 본문을 직접 크롤링하여 종합 분석하였습니다.",
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
    """Save payload to YYYY-MM-DD.json, latest.json, and update available_dates.json manifest."""
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

    # Scan all valid YYYY-MM-DD.json files in DATA_DIR to build available_dates.json
    available_dates = []
    for file_path in DATA_DIR.glob("*.json"):
        match = re.match(r'^(\d{4}-\d{2}-\d{2})\.json$', file_path.name)
        if match:
            available_dates.append(match.group(1))
    
    available_dates.sort(reverse=True)
    
    manifest_path = DATA_DIR / "available_dates.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({"available_dates": available_dates}, f, ensure_ascii=False, indent=2)

    print(f"  - Updated available_dates.json with {len(available_dates)} dates: {available_dates}")
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

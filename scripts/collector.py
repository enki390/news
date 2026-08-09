import os
import json
import re
import datetime
import random
import urllib.parse
from pathlib import Path
import feedparser
import requests
from bs4 import BeautifulSoup

# Configuration
DATA_DIR = Path(__file__).parent.parent / "data"
RETENTION_DAYS = 30

ALLOWED_CATEGORIES = ["경제", "글로벌"]

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
}

# Category-specific RSS Feeds across Major Korean Outlets (경제, 글로벌)
CATEGORY_FEEDS = [
    # 1. 경제
    {"category": "경제", "name": "매일경제", "url": "https://www.mk.co.kr/rss/30000001/"},
    {"category": "경제", "name": "한겨레", "url": "https://www.hani.co.kr/rss/economy/"},
    {"category": "경제", "name": "동아일보", "url": "https://rss.donga.com/economy.xml"},
    {"category": "경제", "name": "경향신문", "url": "https://www.khan.co.kr/rss/rssdata/economy.xml"},
    {"category": "경제", "name": "연합뉴스", "url": "https://www.yna.co.kr/rss/economy.xml"},
    {"category": "경제", "name": "Google News 경제", "url": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko"},

    # 2. 글로벌
    {"category": "글로벌", "name": "한겨레", "url": "https://www.hani.co.kr/rss/international/"},
    {"category": "글로벌", "name": "경향신문", "url": "https://www.khan.co.kr/rss/rssdata/kh_world.xml"},
    {"category": "글로벌", "name": "연합뉴스", "url": "https://www.yna.co.kr/rss/international.xml"},
    {"category": "글로벌", "name": "Google News 글로벌", "url": "https://news.google.com/rss/headlines/section/topic/WORLD?hl=ko&gl=KR&ceid=KR:ko"}
]

def clean_html(text):
    """Remove HTML tags, strip RSS snippet junk, and clean up whitespace."""
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    
    for tag in soup.find_all(['ol', 'ul', 'table', 'script', 'style', 'header', 'footer', 'nav', 'iframe']):
        tag.decompose()
        
    cleaned = soup.get_text(separator=" ").strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = re.sub(r'(\s+[가-힣A-Za-z0-9]+일보|\s+YTN|\s+MBC|\s+KBS|\s+SBS|\s+뉴시스|\s+아주경제|\s+뉴스1|\s+연합뉴스).*$', '', cleaned)
    return cleaned.strip()

def fetch_article_content(url):
    """Fetch full body text of a news article via HTTP web crawling."""
    if not url:
        return ""
    try:
        resp = requests.get(url, headers=HTTP_HEADERS, timeout=5, allow_redirects=True)
        if resp.status_code != 200:
            return ""
        
        if resp.encoding is None or resp.encoding.lower() == 'iso-8859-1':
            resp.encoding = resp.apparent_encoding or 'utf-8'

        soup = BeautifulSoup(resp.text, "html.parser")
        
        for tag in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'iframe', 'aside', 'form', 'figcaption']):
            tag.decompose()

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
    """Fetch headlines and full text content via RSS and Web Crawling for 경제 and 글로벌 categories."""
    raw_articles = []
    print("[1/5] Fetching RSS headlines and crawling article body texts for categories: 경제, 글로벌...")

    for feed_info in CATEGORY_FEEDS:
        try:
            print(f"  - Fetching [{feed_info['category']}] {feed_info['name']}...")
            feed = feedparser.parse(feed_info['url'])
            count = 0
            for entry in feed.entries:
                if count >= 8:
                    break
                title = entry.get('title', '')
                link = entry.get('link', '')
                summary_raw = entry.get('summary', entry.get('description', ''))
                
                if not title or not link:
                    continue

                clean_title, pub_name = parse_publisher_from_title(title, feed_info['name'])
                summary_clean = clean_html(summary_raw)
                
                # Fetch article body text via web crawling
                full_body = fetch_article_content(link)
                
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
                    "full_content": effective_content[:2000],
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
            
            if len(intersection) >= 2 or (art1['target_category'] == art2['target_category'] and len(intersection) >= 1):
                current_cluster.append(art2)
                processed_indices.add(j)

        clusters.append(current_cluster)

    clusters.sort(key=lambda c: len(c), reverse=True)
    return clusters

def summarize_with_gemini(cluster, api_key):
    """Summarize cluster using Gemini API following the new structure rules:
       - overview (수집 기사 전체 요약)
       - differences (언론사별 보도 시작 & 강조점 비교)
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}

    articles_text = ""
    for idx, art in enumerate(cluster):
        body = art.get('full_content', art.get('summary', ''))
        articles_text += f"기사 {idx+1} [언론사: {art['publisher']}]\n제목: {art['title']}\n크롤링된 본문: {body}\n링크: {art['url']}\n\n"

    target_cat = cluster[0].get('target_category', '경제')
    if target_cat not in ALLOWED_CATEGORIES:
        target_cat = '경제'

    prompt = f"""다음은 동일한 주제를 다룬 뉴스 기사들의 실제 크롤링 본문 모음입니다.
수집된 기사 본문을 바탕으로 아래 지침에 따라 브리핑 리포트를 작성해 주세요.

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

def build_fallback_summary(cluster):
    """Fallback summary generator satisfying updated report structure."""
    primary = cluster[0]
    headline = primary['title']
    cat = primary.get('target_category', '경제')
    if cat not in ALLOWED_CATEGORIES:
        cat = '경제'

    all_bodies = [art.get('full_content', art.get('summary', '')) for art in cluster if art.get('full_content') or art.get('summary')]

    if len(all_bodies) >= 2:
        overview = f"{all_bodies[0][:150]}... 한편 {all_bodies[1][:150]}... 수집된 언론사별 기사 본문을 종합하여 현 사안의 전개 방향을 모니터링하고 있습니다."
    elif len(all_bodies) == 1:
        overview = f"{all_bodies[0][:200]}... 주요 언론을 통해 사안의 구체적인 경과가 전달되었습니다."
    else:
        overview = f"{headline} 이슈와 관련하여 주요 언론 매체들이 집중 취재 보도를 진행하고 있습니다."

    differences = []
    for art in cluster:
        pub_name = art['publisher']
        if any(d['publisher'] == pub_name for d in differences):
            continue
        
        body_text = art.get('full_content', art.get('summary', ''))
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', body_text) if len(s.strip()) > 10]
        
        start_pt = sentences[0] if sentences else f"{pub_name}에서 {art['title']} 보도를 시작했습니다."
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

def process_news_clusters(clusters):
    """Process clusters into news items with updated structure (Overview, Random Featured Article Body, Differences)."""
    api_key = os.environ.get("GEMINI_API_KEY")
    news_items = []

    print(f"[2/5] Processing {len(clusters)} topic clusters for categories (경제, 글로벌)...")

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

        # Randomly select one article from the cluster for full body output requirement
        random_art = random.choice(cluster)
        featured_article = {
            "publisher": random_art['publisher'],
            "title": random_art['title'],
            "full_content": random_art.get('full_content', random_art.get('summary', '')),
            "url": random_art['url']
        }

        item_id = f"news-{datetime.date.today().strftime('%Y%m%d')}-{len(news_items)+1:03d}"

        news_items.append({
            "id": item_id,
            "headline": summary_data.get("headline", cluster[0]['title']),
            "category": category,
            "summary": {
                "overview": summary_data.get("overview", ""),
                "featured_article": featured_article,
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
    print(f"=== RSS & Crawling News Collector Batch Starting at {datetime.datetime.now()} ===")
    
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

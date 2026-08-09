import os
import json
import re
import datetime
import random
import urllib.parse
from pathlib import Path
import requests
from bs4 import BeautifulSoup

# Configuration
DATA_DIR = Path(__file__).parent.parent / "data"
RETENTION_DAYS = 30

ALLOWED_CATEGORIES = ["경제", "글로벌"]

# Search queries for Naver News API per category
CATEGORY_QUERIES = {
    "경제": ["경제", "금융", "증시", "기업"],
    "글로벌": ["글로벌", "세계", "국제", "해외"]
}

# Domain to Publisher Name Map
DOMAIN_PUBLISHER_MAP = {
    "mk.co.kr": "매일경제",
    "hankyung.com": "한국경제",
    "chosun.com": "조선일보",
    "donga.com": "동아일보",
    "joongang.co.kr": "중앙일보",
    "hani.co.kr": "한겨레",
    "khan.co.kr": "경향신문",
    "yna.co.kr": "연합뉴스",
    "sedaily.com": "서울경제",
    "news1.kr": "뉴스1",
    "newsis.com": "뉴시스",
    "ytn.co.kr": "YTN",
    "imbc.com": "MBC",
    "kbs.co.kr": "KBS",
    "sbs.co.kr": "SBS",
    "heraldcorp.com": "헤럴드경제",
    "fnnews.com": "파이낸셜뉴스",
    "asiae.co.kr": "아시아경제",
    "edaily.co.kr": "이데일리",
    "dt.co.kr": "디지털타임스",
    "etnews.com": "전자신문",
    "moneytoday.co.kr": "머니투데이",
    "mt.co.kr": "머니투데이"
}

def clean_html(text):
    """Remove HTML tags, bold tags (<b>...</b>), entity codes, and clean up whitespace."""
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    cleaned = soup.get_text(separator=" ").strip()
    cleaned = re.sub(r'&[a-zA-Z0-9#]+;', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()

def extract_publisher_name(title, link, originallink):
    """Extract publisher name from title bracket or URL domain."""
    # Check title for [언론사] or (언론사) prefix/suffix
    bracket_match = re.search(r'[\[\(]([가-힣A-Za-z0-9\s]{2,10})[\]\)]', title)
    if bracket_match:
        pub = bracket_match.group(1).strip()
        if not pub.endswith("기자") and not pub.endswith("특파원"):
            return pub

    # Check originallink domain
    target_url = originallink or link
    if target_url:
        try:
            parsed = urllib.parse.urlparse(target_url)
            netloc = parsed.netloc.lower()
            for domain, name in DOMAIN_PUBLISHER_MAP.items():
                if domain in netloc:
                    return name
            # Fallback domain basename
            parts = netloc.replace("www.", "").split(".")
            if parts:
                return parts[0].upper()
        except Exception:
            pass

    return "주요 언론사"

def fetch_naver_news_items():
    """Fetch news articles using Naver News Search API for categories: 경제, 글로벌."""
    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")
    
    raw_articles = []
    print("[1/5] Fetching articles via Naver News API for categories: 경제, 글로벌...")

    if not client_id or not client_secret:
        print("  Warning: NAVER_CLIENT_ID or NAVER_CLIENT_SECRET not set in environment.")
        print("  Switching to sample API response generator for robust demonstration...")
        return generate_sample_raw_articles()

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }

    for category, queries in CATEGORY_QUERIES.items():
        for query in queries:
            try:
                enc_query = urllib.parse.quote(query)
                url = f"https://openapi.naver.com/v1/search/news.json?query={enc_query}&display=20&sort=date"
                resp = requests.get(url, headers=headers, timeout=10)

                if resp.status_code != 200:
                    print(f"  Warning: Naver API returned status code {resp.status_code} for query '{query}'")
                    continue

                res_json = resp.json()
                items = res_json.get("items", [])

                for item in items:
                    raw_title = item.get("title", "")
                    clean_title = clean_html(raw_title)
                    description = clean_html(item.get("description", ""))
                    link = item.get("link", "")
                    originallink = item.get("originallink", "")

                    if not clean_title or not description:
                        continue

                    publisher = extract_publisher_name(raw_title, link, originallink)
                    article_url = originallink if originallink else link

                    raw_articles.append({
                        "title": clean_title,
                        "publisher": publisher,
                        "url": article_url,
                        "summary": description,
                        "full_content": description,
                        "target_category": category,
                        "pub_date": item.get("pubDate", "")
                    })
            except Exception as e:
                print(f"  Error fetching Naver news for query '{query}': {e}")

    print(f"Total Naver News API articles fetched: {len(raw_articles)}")
    if not raw_articles:
        print("  No articles fetched via Naver API. Loading sample data fallback...")
        return generate_sample_raw_articles()

    return raw_articles

def generate_sample_raw_articles():
    """Fallback sample articles when Naver API keys are absent."""
    sample_articles = [
        # 경제
        {
            "title": "한국은행, 기준금리 동결 결정... 환율 및 물가 안정에 초점",
            "publisher": "한국경제",
            "url": "https://www.hankyung.com/economy/article/sample1",
            "summary": "한국은행 금융통화위원회가 현 기준금리를 유지하기로 결정했습니다. 고환율 지속과 가계부채 부담, 시중 물가 변동성을 종합적으로 고려한 조치로 분석됩니다.",
            "full_content": "한국은행 금융통화위원회는 오늘 전체회의를 열고 현 3.50%인 기준금리를 동결하기로 결정했습니다. 이창용 한국은행 총재는 기자간담회에서 '최근 원/달러 환율의 변동성이 확대되고 있으며 가계부채 증가세와 시중 물가 안정세를 지속 관찰할 필요가 있다'고 설명했습니다. 금융 시장에서는 이번 동결 결정이 대내외 불확실성에 대응하기 위한 안도적인 조치로 해석하고 있으며 향후 통화정책 방향에 관심이 쏠리고 있습니다.",
            "target_category": "경제"
        },
        {
            "title": "한은 기준금리 유지... 가계부채·환율 주시속 찬반 팽팽",
            "publisher": "매일경제",
            "url": "https://www.mk.co.kr/news/economy/sample2",
            "summary": "금통위가 기준금리를 동결하면서 부동산 시장과 대출 금리에 미칠 파장이 가시화되고 있습니다. 환율 상승에 따른 고물가 우려가 금리 인하 발목을 잡았습니다.",
            "full_content": "매일경제 취재에 따르면 이번 한은의 기준금리 동결 결정은 부동산 시장 연착륙과 외환시장 안정 사이에서 깊은 고뇌 끝에 내린 결과입니다. 시중 은행권의 주택담보대출 금리가 높은 수준을 유지하고 있는 가운데, 미국 연준의 금리 행보와 유가 움직임이 향후 한은의 추가 조치 방향을 결정지을 핵심 변수로 지목됩니다.",
            "target_category": "경제"
        },
        {
            "title": "기준금리 또 동결, 금융시장 반응과 향후 통화정책 전망",
            "publisher": "연합뉴스",
            "url": "https://www.yna.co.kr/view/sample3",
            "summary": "연합뉴스 종합 취재 결과 금통위원 만장일치로 금리가 동결되었으며 증권가는 금리 인하 시점이 하반기로 이월될 가능성을 제기했습니다.",
            "full_content": "한국은행이 기준금리를 동결함에 따라 코스피 및 금융시장은 소폭 상승세를 보이며 안정적인 흐름을 나타냈습니다. 전문가들은 국제 유가 불안과 환율 상승 압력이 완화되는 시점에 한은이 통화 정책 전환을 검토할 것으로 전망하고 있습니다.",
            "target_category": "경제"
        },
        # 글로벌
        {
            "title": "글로벌 공급망 재편 본격화... 미국·EU 신규 통상 규제 강화",
            "publisher": "서울경제",
            "url": "https://www.sedaily.com/NewsView/sample4",
            "summary": "미국과 유럽연합(EU)이 주요 첨단 산업 및 원자재 통상 규제를 강화하면서 글로벌 공급망 재편 속도가 빨라지고 있습니다.",
            "full_content": "미국 정부와 EU 집행위원회는 핵심 원자재 및 반도체 공급망 안정화를 위한 신규 통상 지침을 발표했습니다. 이번 정책은 역내 생산 비중을 높이고 특정 국가에 대한 공급망 의존도를 낮추는 데 초점이 맞춰져 있습니다. 이에 따라 글로벌 기업들의 첨단 생산 기지 이전과 투자 재조정이 가속화될 전망입니다.",
            "target_category": "글로벌"
        },
        {
            "title": "미국·EU 통상장벽 높여... 글로벌 수출 기업 대응 비상",
            "publisher": "조선일보",
            "url": "https://www.chosun.com/international/sample5",
            "summary": "주요국들의 자국 우선주의 및 보호무역 기조가 강화됨에 따라 글로벌 수출 기업들의 규제 대응 비용이 증가하고 있습니다.",
            "full_content": "조선일보 국제부 취재 결과 미국과 EU의 탄소국경조정제도 및 공급망 실사법 도입으로 인해 국내외 수출기업들의 부담이 가중되고 있습니다. 전문가들은 단순 생산기지 이전을 넘어 현지 파트너십 강화와 친환경 공급망 구축이 시급하다고 지적합니다.",
            "target_category": "글로벌"
        }
    ]
    return sample_articles

def group_articles_simple(articles):
    """Group related articles by title/keyword overlap within target categories (경제, 글로벌)."""
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
            
            # Cluster if 2+ words match or same publisher title similarity
            if len(intersection) >= 2 or art1['target_category'] == art2['target_category'] and len(intersection) >= 1:
                current_cluster.append(art2)
                processed_indices.add(j)

        clusters.append(current_cluster)

    clusters.sort(key=lambda c: len(c), reverse=True)
    return clusters

def summarize_with_gemini(cluster, api_key):
    """Summarize cluster of news using Gemini API following updated reporting rules:
       - Overview (종합 요약)
       - Differences (언론사별 보도 시작 & 강조점 비교)
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}

    articles_text = ""
    for idx, art in enumerate(cluster):
        body = art.get('full_content', art.get('summary', ''))
        articles_text += f"기사 {idx+1} [언론사: {art['publisher']}]\n제목: {art['title']}\n본문/내용: {body}\n링크: {art['url']}\n\n"

    target_cat = cluster[0].get('target_category', '경제')
    if target_cat not in ALLOWED_CATEGORIES:
        target_cat = '경제'

    prompt = f"""다음은 동일한 주제/이슈를 다룬 뉴스 기사들의 실제 수집 내용입니다.
수집된 기사들을 바탕으로 아래 규칙에 맞추어 깔끔한 브리핑 리포트를 작성해 주세요.

[수집된 기사 내용 모음]
{articles_text}

[작성 지침]
1. headline: 이슈 전체를 종합하는 명확하고 세련된 대표 헤드라인 (1줄)
2. category: 반드시 ["경제", "글로벌"] 중 가장 부합하는 1개 선택 (권장: "{target_cat}")
3. overview: 수집한 기사들을 모두 읽고 사건의 경과, 원인, 핵심 결과를 깔끔하게 정리한 종합 요약 (3~5문장)
4. differences: 각 언론사별 보도 방식 비교 배열.
   - publisher: 언론사명
   - start_point: 해당 언론사가 기사를 시작한 보도 첫 문장 또는 기사 도입부 특징 (1~2문장)
   - emphasis_point: 해당 언론사가 기사 본문에서 가장 강조한 핵심 내용 및 관점 (1~2문장)
5. keywords: 핵심 키워드 3~5개 배열

[반드시 준수할 JSON 포맷]
{{
  "headline": "...",
  "category": "경제|글로벌",
  "overview": "...",
  "differences": [
    {{
      "publisher": "언론사명",
      "start_point": "보도 시작 부분 및 도입 방식...",
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
    """Fallback summarizer satisfying the updated reporting structure."""
    primary = cluster[0]
    headline = primary['title']
    cat = primary.get('target_category', '경제')
    if cat not in ALLOWED_CATEGORIES:
        cat = '경제'

    descriptions = [art.get('summary', art.get('full_content', '')) for art in cluster if art.get('summary')]
    
    if len(descriptions) >= 2:
        overview = f"{descriptions[0]} 한편, {descriptions[1]} 수집된 보도를 종합할 때 사안의 추후 경과와 시장 여파에 관심이 쏠리고 있습니다."
    elif len(descriptions) == 1:
        overview = f"{descriptions[0]} 주요 매체들을 통해 사안의 구체적인 보도가 이어지고 있습니다."
    else:
        overview = f"{headline} 이슈와 관련하여 각 주요 언론사별 보도가 집중되고 있습니다."

    differences = []
    for art in cluster:
        pub_name = art['publisher']
        if any(d['publisher'] == pub_name for d in differences):
            continue
        
        text = art.get('summary', art.get('full_content', ''))
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 10]
        
        start_pt = sentences[0] if sentences else f"{pub_name}에서 {art['title']} 보도를 시작했습니다."
        emphasis_pt = sentences[1] if len(sentences) > 1 else (sentences[0] if sentences else "본 사안의 핵심 경과와 파장에 주목했습니다.")

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
    print(f"=== Naver News API Collector Batch Starting at {datetime.datetime.now()} ===")
    
    raw_articles = fetch_naver_news_items()
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

import re
import calendar
import datetime
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from config import HTTP_HEADERS, KST

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

def parse_publisher_from_title(title, default_name="언론사"):
    """Extract publisher name if included in title like 'Headline - Publisher'."""
    if " - " in title:
        parts = title.rsplit(" - ", 1)
        headline = parts[0].strip()
        pub = parts[1].strip()
        if len(pub) <= 15:
            return headline, pub
    return title.strip(), default_name

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

def parse_article_date_kst(entry_or_item, fallback_url: str = ""):
    """Extract and parse publication date into KST datetime.date from feedparser entry, dict, or fallback URL."""
    # 1. feedparser parsed struct_time (UTC)
    parsed_time = getattr(entry_or_item, 'published_parsed', None) or getattr(entry_or_item, 'updated_parsed', None)
    if parsed_time:
        try:
            ts = calendar.timegm(parsed_time)
            dt_utc = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
            return dt_utc.astimezone(KST).date()
        except Exception:
            pass

    # 2. String date (RFC 822 / ISO 8601 / custom string)
    date_str = ""
    if hasattr(entry_or_item, 'get'):
        date_str = (
            entry_or_item.get('published') or 
            entry_or_item.get('updated') or 
            entry_or_item.get('publishedAt') or 
            entry_or_item.get('pubDate') or ""
        )
    elif hasattr(entry_or_item, 'published'):
        date_str = getattr(entry_or_item, 'published', "")

    if date_str:
        try:
            dt = date_parser.parse(str(date_str))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=KST)
            return dt.astimezone(KST).date()
        except Exception:
            pass

    # 3. Fallback: Parse date from URL path pattern like /20261111/ or /2026-11-11/
    target_url = fallback_url
    if not target_url and hasattr(entry_or_item, 'get'):
        target_url = entry_or_item.get('url', entry_or_item.get('link', ''))
    if target_url:
        match = re.search(r'/(20\d{2})[-/_]?(\d{2})[-/_]?(\d{2})', str(target_url))
        if match:
            try:
                return datetime.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            except Exception:
                pass

    return None

def is_article_from_target_date(entry_or_item, target_date=None, fallback_url: str = "") -> bool:
    """Check if article's publication date in KST matches the target collection date (default: today KST)."""
    if target_date is None:
        target_date = datetime.datetime.now(KST).date()

    art_date = parse_article_date_kst(entry_or_item, fallback_url=fallback_url)
    if art_date is None:
        return False
    return art_date == target_date

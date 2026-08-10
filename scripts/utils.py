import re
import requests
from bs4 import BeautifulSoup
from config import HTTP_HEADERS

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

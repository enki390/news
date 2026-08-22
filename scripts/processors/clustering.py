import re
from typing import List
from kiwipiepy import Kiwi
from sources.base import NewsArticle

_kiwi = None

def get_kiwi() -> Kiwi:
    global _kiwi
    if _kiwi is None:
        _kiwi = Kiwi()
    return _kiwi

def extract_noun_keywords(text: str) -> set:
    """Extract Korean nouns (NNG, NNP) of length >= 2 using Kiwipiepy."""
    if not text:
        return set()
    try:
        kiwi = get_kiwi()
        tokens = kiwi.tokenize(text)
        nouns = {
            t.form for t in tokens 
            if t.tag in ('NNG', 'NNP') and len(t.form) >= 2
        }
        return nouns
    except Exception as e:
        print(f"[clustering] Kiwi tokenization fallback: {e}")
        return set(re.findall(r'[가-힣A-Za-z0-9]{2,}', text))

def group_articles_simple(articles: List[NewsArticle]) -> List[List[NewsArticle]]:
    """Group related articles by noun keyword overlap (>= 2 matching nouns) within categories."""
    clusters = []
    processed_indices = set()

    article_nouns = [extract_noun_keywords(art.title) for art in articles]

    for i, art1 in enumerate(articles):
        if i in processed_indices:
            continue

        nouns1 = article_nouns[i]
        current_cluster = [art1]
        processed_indices.add(i)

        for j, art2 in enumerate(articles):
            if j in processed_indices:
                continue

            nouns2 = article_nouns[j]
            intersection = nouns1.intersection(nouns2)
            
            if len(intersection) >= 2:
                current_cluster.append(art2)
                processed_indices.add(j)

        clusters.append(current_cluster)

    # Sort clusters by article count descending (ranking score by popularity/coverage)
    clusters.sort(key=lambda c: len(c), reverse=True)
    return clusters

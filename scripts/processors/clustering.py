import re
from typing import List
from sources.base import NewsArticle

def group_articles_simple(articles: List[NewsArticle]) -> List[List[NewsArticle]]:
    """Group related articles by title/keyword overlap within categories."""
    clusters = []
    processed_indices = set()

    for i, art1 in enumerate(articles):
        if i in processed_indices:
            continue

        words1 = set(re.findall(r'[가-힣A-Za-z0-9]{2,}', art1.title))
        current_cluster = [art1]
        processed_indices.add(i)

        for j, art2 in enumerate(articles):
            if j in processed_indices:
                continue

            words2 = set(re.findall(r'[가-힣A-Za-z0-9]{2,}', art2.title))
            intersection = words1.intersection(words2)
            
            if len(intersection) >= 2 or (art1.target_category == art2.target_category and len(intersection) >= 1):
                current_cluster.append(art2)
                processed_indices.add(j)

        clusters.append(current_cluster)

    clusters.sort(key=lambda c: len(c), reverse=True)
    return clusters

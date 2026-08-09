---
name: collect-news
description: Run the python news collector script to fetch RSS feeds and summarize news with Gemini AI
---

# News Collector Skill

Use this skill when you need to run or test the news collector script locally or check data generation.

## Workflow

1. Ensure dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the collector script:
   ```bash
   python scripts/collector.py
   ```

3. Verify generated output in `data/news.json`.

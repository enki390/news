import json
import re
import datetime
from config import DATA_DIR, RETENTION_DAYS

def clean_old_files():
    """Delete news JSON files older than 30 days."""
    print("Cleaning files older than 30 days...")
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

def save_daily_news(news_items):
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

    print(f"Saving daily news JSON ({len(news_items)} items) to {output_path}...")
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

import feedparser
import requests
import os
from urllib.parse import quote

RSS_URL = "https://developer.apple.com/news/releases/rss/releases.rss"
CACHE_FILE = "last_update_id.txt"

def load_last_id():
    try:
        with open(CACHE_FILE, "r") as f:
            return f.read().strip()
    except:
        return ""

def save_last_id(eid):
    with open(CACHE_FILE, "w") as f:
        f.write(eid)

def main():
    feed = feedparser.parse(RSS_URL)
    entries = feed.entries[:15]

    last_id = load_last_id()
    new_items = []

    for item in entries:
        eid = item.get("id") or item.get("link")  # fallback
        if eid == last_id:
            break
        new_items.append(item)

    # 初次运行保护：只推最新的一个
    if not last_id and new_items:
        new_items = [entries[0]]

    if not new_items:
        print("No new updates.")
        return

    print(f"Found {len(new_items)} new updates.")

    bark_key = os.getenv("BARK_KEY")
    push_base = f"https://api.day.app/{bark_key}"

    for item in new_items[::-1]:
        title = quote("Apple软件更新")
        body = quote(item.title)
        link = quote(item.link, safe="")
        url = f"{push_base}/{title}/{body}?url={link}&group=AppleUpdate"

        r = requests.get(url)
        print(f"Pushed: {item.title}, status={r.status_code}")

    # 保存最新 ID
    newest_id = entries[0].get("id") or entries[0].get("link")
    save_last_id(newest_id)

if __name__ == "__main__":
    main()


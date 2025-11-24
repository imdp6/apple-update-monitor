import feedparser
import requests
import os

# Apple Developer Releases RSS URL
RSS_URL = 'https://developer.apple.com/news/releases/rss/releases.rss'
CACHE_FILE = 'last_update_id.txt'

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

    # 获取本次运行之前的最后更新 ID
    last_id = load_last_id()

    new_items = []
    for item in feed.entries:
        eid = item.get("id") or item.get("link")  # 使用 link 作为备用 ID
        if eid == last_id:
            break
        new_items.append(item)

    # 如果没有新条目
    if not new_items:
        print("No new updates.")
        return

    print(f"Found {len(new_items)} new updates.")

    bark_key = os.getenv("BARK_KEY")
    push_base = f"https://api.day.app/{bark_key}"

    # 逐条推送更新内容
    for item in new_items[::-1]:  # 从旧到新推送
        title = item.title
        body = item.title
        link = item.link
        url = f"{push_base}/{title}/{body}?url={link}&group=AppleUpdate"

        r = requests.get(url)
        print(f"Pushed: {item.title}, status={r.status_code}")

    # 更新本次最新的条目 ID
    newest_id = feed.entries[0].get("id") or feed.entries[0].get("link")
    save_last_id(newest_id)

if __name__ == "__main__":
    main()

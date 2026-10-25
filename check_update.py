import feedparser
import requests
import os
import time
import sys
from urllib.parse import quote

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

def fetch_rss_with_retry(url, retries=6, delay=10):
    """
    尝试获取 RSS 数据，最多重试 `retries` 次，失败时每次延迟 `delay` 秒
    """
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=(10, 30))
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            if feed.entries:
                return feed
            print(f"Attempt {attempt + 1} failed, no entries found, retrying...")
        except Exception as e:
            print(f"Attempt {attempt + 1} failed with error: {e}, retrying...")
        
        # 如果没有成功，等待一段时间后重试
        if attempt + 1 < retries:
            time.sleep(delay)
    return None

def push_update(bark_key, item):
    title = item.title
    body = f"{title} ({item.get('published', 'Unknown Date')})"
    url = f"https://api.day.app/{quote(bark_key, safe='')}/{quote(title, safe='')}/{quote(body, safe='')}"
    try:
        response = requests.get(
            url, params={"url": item.link, "group": "AppleUpdate"}, timeout=10
        )
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict) or result.get("code") != 200:
            raise ValueError("Bark rejected notification")
    except (requests.RequestException, ValueError) as exc:
        # Request exceptions may include the URL containing the secret key.
        raise RuntimeError(f"Failed to push {title}: {type(exc).__name__}") from None
    print(f"Pushed: {body}, status={response.status_code}")

def main():
    # 尝试获取 RSS 数据
    feed = fetch_rss_with_retry(RSS_URL, retries=6)  # 设置重试次数为 6 次
    if not feed:
        raise RuntimeError("Failed to fetch RSS data after multiple attempts.")

    # 获取本次运行之前的最后更新 ID
    last_id = load_last_id()

    # 获取最新条目的发布时间作为基准日期
    if not feed.entries:
        return
        
    latest_entry = feed.entries[0]
    if not hasattr(latest_entry, 'published_parsed'):
        raise RuntimeError("Unable to parse published date.")
        
    latest_date = latest_entry.published_parsed[:3] # (year, month, day)

    new_items = []
    for item in feed.entries:
        eid = item.get("id") or item.get("link")
        if eid == last_id:
            break
            
        # 检查日期是否与最新条目一致
        if hasattr(item, 'published_parsed'):
            item_date = item.published_parsed[:3]
            if item_date != latest_date:
                continue
                
        new_items.append(item)

    # 如果没有新条目
    if not new_items:
        print("No new updates.")
        return

    print(f"Found {len(new_items)} new updates.")

    bark_key = os.getenv("BARK_KEY")
    if not bark_key:
        raise RuntimeError("BARK_KEY is not set in environment variables.")

    # 逐条推送更新内容
    for item in new_items[::-1]:  # 从旧到新推送
        push_update(bark_key, item)

    # 更新本次最新的条目 ID
    newest_id = feed.entries[0].get("id") or feed.entries[0].get("link")
    save_last_id(newest_id)

if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

import json
import os
import sys
import urllib.parse
import urllib.request
import feedparser

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
SEEN_PATH = os.path.join(os.path.dirname(__file__), "seen.json")

NTFY_TOPIC = os.environ.get("NTFY_TOPIC")
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}" if NTFY_TOPIC else None


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_news(keyword):
    query = urllib.parse.quote(keyword)
    url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(url)
    return feed.entries


def send_push(title, link, keyword):
    if not NTFY_URL:
        print(f"[DRY-RUN] {keyword}: {title} -> {link}")
        return

    headers = {
        "Title": f"[{keyword}] HLB 뉴스".encode("utf-8"),
        "Click": link.encode("utf-8"),
        "Content-Type": "text/plain; charset=utf-8",
    }
    req = urllib.request.Request(
        NTFY_URL, data=title.encode("utf-8"), headers=headers, method="POST"
    )
    urllib.request.urlopen(req)


def main():
    config = load_json(CONFIG_PATH, {"keywords": ["HLB"]})
    seen = load_json(SEEN_PATH, {})

    keywords = config.get("keywords", [])
    new_count = 0

    for keyword in keywords:
        seen_ids = set(seen.get(keyword, []))
        is_first_run = len(seen_ids) == 0

        entries = fetch_news(keyword)
        new_ids = []

        for entry in entries:
            entry_id = entry.get("id") or entry.get("link")
            if entry_id in seen_ids:
                continue

            new_ids.append(entry_id)

            if not is_first_run:
                send_push(entry.title, entry.link, keyword)
                new_count += 1

        seen_ids.update(new_ids)
        # Keep the seen set from growing forever
        seen[keyword] = list(seen_ids)[-500:]

        if is_first_run:
            print(f"[{keyword}] 첫 실행: 기존 기사 {len(new_ids)}개를 읽음 처리 (알림 없음)")
        else:
            print(f"[{keyword}] 새 기사 {len(new_ids)}개")

    save_json(SEEN_PATH, seen)
    print(f"총 알림 전송: {new_count}건")


if __name__ == "__main__":
    main()

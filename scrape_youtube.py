#!/usr/bin/env python3
"""
YouTube 最新動画 自動取得スクリプト
=====================================
チャンネルのRSSフィードから最新動画を取得し、
youtube_posts.json に保存します。APIキー不要。

【使い方】
  pip3 install requests
  python3 scrape_youtube.py

【チャンネルIDの確認方法】
  1. https://www.youtube.com/@good_luck044 をブラウザで開く
  2. Ctrl+U でソースを表示
  3. "channelId" を検索すると "UC..." 形式のIDが見つかります
  4. 下の CHANNEL_ID に貼り付けてください
"""

import json
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

try:
    import requests
except ImportError:
    print("requestsが必要です: pip3 install requests")
    sys.exit(1)

# ── 設定 ──────────────────────────────────────────────────────────────
# ★ ここにチャンネルIDを入力してください（"UC" で始まる文字列）
CHANNEL_ID   = "UCw1bfo8sib9TJa4GLH-h6lg"   # @good_luck044
OUTPUT_FILE  = Path(__file__).parent / "youtube_posts.json"
MAX_VIDEOS   = 12   # 取得する最大動画数
# ─────────────────────────────────────────────────────────────────────

RSS_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"

NS = {
    "atom":   "http://www.w3.org/2005/Atom",
    "media":  "http://search.yahoo.com/mrss/",
    "yt":     "http://www.youtube.com/xml/schemas/2015",
}


def fetch_rss() -> list:
    print(f"📡 YouTubeのRSSを取得中... ({RSS_URL})")
    try:
        resp = requests.get(RSS_URL, timeout=15,
                            headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ ネットワークエラー: {e}")
        return []

    root = ET.fromstring(resp.content)
    entries = root.findall("atom:entry", NS)
    print(f"   → {len(entries)} 件の動画エントリを取得")

    videos = []
    for entry in entries[:MAX_VIDEOS]:
        video_id = entry.findtext("yt:videoId", namespaces=NS, default="")
        title    = entry.findtext("atom:title", namespaces=NS, default="")
        pub      = entry.findtext("atom:published", namespaces=NS, default="")
        link_el  = entry.find("atom:link", NS)
        url      = link_el.get("href", "") if link_el is not None else ""

        # サムネイル
        thumb_el = entry.find(".//media:thumbnail", NS)
        thumb    = thumb_el.get("url", "") if thumb_el is not None else \
                   f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"

        # 説明文
        desc_el = entry.find(".//media:description", NS)
        desc    = (desc_el.text or "")[:200] if desc_el is not None else ""

        videos.append({
            "videoId":     video_id,
            "title":       title,
            "publishedAt": pub,
            "url":         url,
            "thumbnail":   thumb,
            "description": desc,
        })

    return videos


def main():
    print("=" * 55)
    print("  YouTube動画取得スクリプト")
    print(f"  チャンネルID: {CHANNEL_ID}")
    print("=" * 55)
    print()

    if CHANNEL_ID == "YOUR_CHANNEL_ID_HERE":
        print("❌ CHANNEL_ID が未設定です。")
        print("   スクリプト上部の CHANNEL_ID に実際のIDを入力してください。")
        print()
        print("   チャンネルIDの確認方法:")
        print("   1. https://www.youtube.com/@good_luck044 をブラウザで開く")
        print("   2. Ctrl+U でページソースを表示")
        print('   3. "channelId" で検索 → "UC..." 形式のIDをコピー')
        sys.exit(1)

    videos = fetch_rss()
    if not videos:
        print("❌ 動画が取得できませんでした。")
        sys.exit(1)

    # 既存データ読み込み（更新日時を保持）
    existing = {}
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, encoding="utf-8") as f:
            old = json.load(f)
        existing = {v["videoId"]: v for v in old.get("videos", [])}

    # 新規追加カウント
    new_count = sum(1 for v in videos if v["videoId"] not in existing)

    data = {
        "_readme": {
            "説明": "丸吉孝文 YouTube最新動画リスト",
            "自動更新": "GitHub Actions / scrape_youtube.py が毎日更新",
            "最終更新": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "videos": videos,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 55)
    print(f"✨ 完了！ {new_count} 件の新規動画を追加しました")
    print(f"   合計: {len(videos)} 件")
    print("=" * 55)


if __name__ == "__main__":
    main()

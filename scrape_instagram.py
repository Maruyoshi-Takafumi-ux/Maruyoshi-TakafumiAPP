#!/usr/bin/env python3
"""
Instagram 最新投稿 自動取得スクリプト
=======================================
Instagram Graph API を使って最新投稿を取得し、
instagram_posts.json に保存します。

【前提条件】
  - Meta Business アカウント + Instagramプロフェッショナルアカウント連携済み
  - 長期アクセストークン（Long-lived Access Token）の取得が必要

【セットアップ手順】
  1. https://developers.facebook.com/ でアプリを作成
  2. Instagram Graph API の設定
  3. アクセストークンを取得 → 長期トークンに変換（有効期限60日）
  4. GitHubリポジトリの Settings → Secrets → Actions で
     INSTAGRAM_TOKEN という名前でトークンを登録

【使い方（ローカル）】
  export INSTAGRAM_TOKEN="YOUR_TOKEN_HERE"
  python3 scrape_instagram.py

【長期トークン取得コマンド】
  curl -i -X GET "https://graph.instagram.com/access_token
    ?grant_type=ig_exchange_token
    &client_id={APP_ID}
    &client_secret={APP_SECRET}
    &access_token={SHORT_LIVED_TOKEN}"
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

try:
    import requests
except ImportError:
    print("requestsが必要です: pip3 install requests")
    sys.exit(1)

# ── 設定 ──────────────────────────────────────────────────────────────
# GitHubシークレットまたは環境変数からトークンを取得
ACCESS_TOKEN = os.environ.get("INSTAGRAM_TOKEN", "")
OUTPUT_FILE  = Path(__file__).parent / "instagram_posts.json"
MAX_POSTS    = 12   # 取得する最大投稿数
# ─────────────────────────────────────────────────────────────────────

GRAPH_API_BASE = "https://graph.instagram.com/v21.0"
MEDIA_FIELDS   = "id,media_type,media_url,thumbnail_url,permalink,caption,timestamp"


def get_user_id() -> str:
    """自分のユーザーIDを取得"""
    url = f"{GRAPH_API_BASE}/me"
    params = {"fields": "id,name,username", "access_token": ACCESS_TOKEN}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    print(f"   ユーザー: @{data.get('username', 'unknown')} (ID: {data['id']})")
    return data["id"]


def fetch_posts(user_id: str) -> list:
    """メディア一覧を取得"""
    url = f"{GRAPH_API_BASE}/{user_id}/media"
    params = {
        "fields": MEDIA_FIELDS,
        "limit": MAX_POSTS,
        "access_token": ACCESS_TOKEN,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    raw = resp.json().get("data", [])
    print(f"   → {len(raw)} 件の投稿を取得")

    posts = []
    for item in raw:
        media_type = item.get("media_type", "")

        # 動画の場合はサムネイル、写真は画像URL
        image_url = item.get("thumbnail_url") or item.get("media_url", "")
        # VIDEO_CAROUSEL等でサムネイルがない場合はスキップしない（URLだけ空にする）

        caption = (item.get("caption") or "")[:200]
        permalink = item.get("permalink", "")
        timestamp = item.get("timestamp", "")

        posts.append({
            "id":         item.get("id", ""),
            "mediaType":  media_type,
            "imageUrl":   image_url,
            "permalink":  permalink,
            "caption":    caption,
            "timestamp":  timestamp,
        })

    return posts


def main():
    print("=" * 55)
    print("  Instagram投稿取得スクリプト")
    print("=" * 55)
    print()

    if not ACCESS_TOKEN:
        print("❌ INSTAGRAM_TOKEN が未設定です。")
        print()
        print("   ローカル実行の場合:")
        print("     export INSTAGRAM_TOKEN='あなたのトークン'")
        print("     python3 scrape_instagram.py")
        print()
        print("   GitHub Actionsの場合:")
        print("     リポジトリ Settings → Secrets → Actions")
        print("     INSTAGRAM_TOKEN を追加してください")
        print()
        print("   【トークン取得方法】")
        print("   1. https://developers.facebook.com/ でアプリ作成")
        print("   2. Instagram Graph API → 「アクセス権を追加」")
        print("   3. アクセストークン取得 → 長期トークンに変換（有効期限60日）")
        sys.exit(1)

    print("📡 Instagramへ接続中...")
    try:
        user_id = get_user_id()
        posts   = fetch_posts(user_id)
    except requests.HTTPError as e:
        if e.response.status_code == 401:
            print("❌ トークンが無効または期限切れです。")
            print("   新しい長期トークンを取得して INSTAGRAM_TOKEN を更新してください。")
        else:
            print(f"❌ APIエラー: {e}")
        sys.exit(1)
    except requests.RequestException as e:
        print(f"❌ ネットワークエラー: {e}")
        sys.exit(1)

    if not posts:
        print("⚠️  投稿が見つかりませんでした。")
        sys.exit(0)

    # 既存データ読み込み
    existing_ids = set()
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, encoding="utf-8") as f:
            old = json.load(f)
        existing_ids = {p["id"] for p in old.get("posts", [])}

    new_count = sum(1 for p in posts if p["id"] not in existing_ids)

    data = {
        "_readme": {
            "説明": "丸吉孝文 Instagram最新投稿リスト",
            "自動更新": "GitHub Actions / scrape_instagram.py が毎日更新",
            "最終更新": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "注意": "アクセストークンの有効期限は60日。期限前に更新が必要。",
        },
        "posts": posts,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 55)
    print(f"✨ 完了！ {new_count} 件の新規投稿を追加しました")
    print(f"   合計: {len(posts)} 件")
    print("=" * 55)


if __name__ == "__main__":
    main()

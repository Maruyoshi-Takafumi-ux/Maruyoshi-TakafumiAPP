#!/usr/bin/env python3
"""
選挙ドットコム ブログ記事 取得スクリプト
==========================================
APIから丸吉孝文さんのブログ記事を全件取得し、
posts.json に追記します。

【使い方】
1. このファイルと posts.json をデスクトップに置く
2. ターミナルで:
   cd ~/Desktop
   pip3 install requests
   python3 scrape_posts.py
"""

import json
import time
import sys
from pathlib import Path
from datetime import datetime

try:
    import requests
except ImportError:
    print("requestsが必要です。以下を実行してください:")
    print("  pip3 install requests")
    sys.exit(1)

# ── 設定 ──────────────────────────────────────────────────────
API_BASE     = "https://api.go2senkyo.com/api/posts/182645"
SITE_BASE    = "https://go2senkyo.com"
POSTS_JSON   = Path(__file__).parent / "posts.json"
NUM_PER_PAGE = 50   # 1回のリクエストで取得する件数
DELAY        = 1.0  # リクエスト間隔（秒）

# ── フィルター設定 ────────────────────────────────────────────
# タイトルにこのキーワードが含まれる記事だけを取得します
# 空リスト [] にすると全記事取得（フィルターなし）
FILTER_KEYWORDS = ["松原"]

# タイトルにこのキーワードが含まれる記事は除外します
EXCLUDE_KEYWORDS = ["花火", "期日前投票状況", "速報", "箕面市長", "茨木市長"]

HEADERS = {
    "Accept":          "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Origin":          "https://go2senkyo.com",
    "Referer":         "https://go2senkyo.com/",
    "User-Agent":      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0.0.0 Safari/537.36",
}

# ── カテゴリー自動判定 ─────────────────────────────────────────
CATEGORY_RULES = [
    (["令和ボイス", "陳情", "声なき声", "ブロードリスニング"], "令和ボイス"),
    (["AI", "DX", "デジタル", "テクノロジー", "動画生成", "ChatGPT"], "AI・DX"),
    (["子ども", "教育", "学び", "子育て", "SEL"], "子育て"),
    (["補助金", "税金", "予算", "財政", "行政", "市役所", "議会", "政策", "公約"], "政策"),
]

def guess_category(title: str) -> str:
    for keywords, cat in CATEGORY_RULES:
        if any(kw in title for kw in keywords):
            return cat
    return "お知らせ"


def parse_date(raw: str) -> str:
    """'2026/4/27 09:15:06' → '2026-04-27'"""
    try:
        dt = datetime.strptime(raw.strip(), "%Y/%m/%d %H:%M:%S")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return datetime.today().strftime("%Y-%m-%d")


# ── posts.json の読み書き ──────────────────────────────────────
def load_json() -> dict:
    if POSTS_JSON.exists():
        with open(POSTS_JSON, encoding="utf-8") as f:
            return json.load(f)
    return {"_readme": {}, "posts": []}


def save_json(data: dict):
    with open(POSTS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def next_id(posts: list) -> int:
    return max((p.get("id", 0) for p in posts), default=0) + 1


# ── API取得 ────────────────────────────────────────────────────
def fetch_all_posts() -> list:
    """ページネーションしながら全記事を取得"""
    all_items = []
    page = 1

    while True:
        url = f"{API_BASE}?num={NUM_PER_PAGE}&p={page}"
        print(f"   ページ {page} 取得中... ({url})")

        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            items = resp.json()
        except requests.RequestException as e:
            print(f"❌ ネットワークエラー: {e}")
            break
        except ValueError:
            print("❌ JSONの解析に失敗しました")
            break

        if not items:  # 空配列 = 最終ページ
            break

        all_items.extend(items)
        print(f"   → {len(items)} 件取得（累計: {len(all_items)} 件）")

        if len(items) < NUM_PER_PAGE:  # 最終ページ
            break

        page += 1
        time.sleep(DELAY)

    return all_items


# ── メイン ────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  選挙ドットコム ブログ取得スクリプト")
    print("  丸吉孝文 / politician ID: 182645")
    print("=" * 55)
    print()

    # API から全記事取得
    print("📡 APIから記事を取得しています...\n")
    raw_posts = fetch_all_posts()

    if not raw_posts:
        print("\n❌ 記事が取得できませんでした。")
        print("   インターネット接続を確認してください。")
        sys.exit(1)

    print(f"\n✅ 合計 {len(raw_posts)} 件の記事を取得しました")

    # フィルタリング
    if FILTER_KEYWORDS:
        filtered = [p for p in raw_posts if any(kw in p.get("title","") for kw in FILTER_KEYWORDS)]
        print(f"🔍 「{'・'.join(FILTER_KEYWORDS)}」を含む記事に絞り込み: {len(filtered)} 件")
    else:
        filtered = raw_posts

    if EXCLUDE_KEYWORDS:
        before = len(filtered)
        filtered = [p for p in filtered if not any(kw in p.get("title","") for kw in EXCLUDE_KEYWORDS)]
        print(f"🚫 除外キーワードで {before - len(filtered)} 件を除外 → {len(filtered)} 件")

    raw_posts = filtered
    print()

    # 既存データ読み込み
    data = load_json()
    existing_ids = {p.get("sourceUrl", "") for p in data["posts"]}
    new_count = 0

    for item in raw_posts:
        source_url = SITE_BASE + item["url"]

        if source_url in existing_ids:
            continue  # 重複スキップ

        title    = item.get("title", "")
        date_raw = item.get("published_at", "")
        thumb    = item.get("thumbnail", "")

        post = {
            "id":        next_id(data["posts"]),
            "title":     title,
            "date":      parse_date(date_raw),
            "category":  guess_category(title),
            "source":    "選挙ドットコム",
            "sourceUrl": source_url,
            "excerpt":   f"{title}の詳細は選挙ドットコムの記事をご覧ください。",
            "content":   "",
            "tags":      [],
            "featured":  False,
            "image":     thumb,
        }

        data["posts"].append(post)
        existing_ids.add(source_url)
        new_count += 1
        print(f"  ＋ {title[:45]}{'…' if len(title) > 45 else ''}")

    # 日付降順でソート
    data["posts"].sort(key=lambda p: p.get("date", ""), reverse=True)

    # 保存
    save_json(data)

    print()
    print("=" * 55)
    print(f"✨ 完了！ {new_count} 件の新規記事を追加しました")
    print(f"   posts.json の合計: {len(data['posts'])} 件")
    print()
    print("次のステップ:")
    print("  index.html と posts.json を")
    print("  GitHub Pages / Vercel にアップロードして完了")
    print("=" * 55)


if __name__ == "__main__":
    main()

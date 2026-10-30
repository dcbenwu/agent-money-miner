#!/usr/bin/env python3
"""Scan agentusecases.ai RSS for money-making use cases.

- Fetches https://agentusecases.ai/feed.xml
- Scores each item with money-signal keywords (strong/medium)
- Dedupes against state/seen.json (by link)
- Writes out/digest-YYYY-MM-DD.md and .json with the top opportunities
- Exit code always 0 unless the fetch itself fails (cron surfaces that)

Stdlib only.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
STATE = BASE / "state"
OUT = BASE / "out"
SEEN = STATE / "seen.json"
FEED_URL = "https://agentusecases.ai/feed.xml"

STRONG = {
    "refund": 3, "unclaimed": 3, "negotiat": 3, "discount": 3, "invoice": 3,
    "tax": 3, "sell": 3, "revenue": 3, "monetiz": 3, "income": 3, "profit": 3,
    "client": 3, "lead": 3, "agency": 3, "outsource": 3, "dropship": 3,
    "arbitrage": 3, "resell": 3, "affiliate": 3, "freelance": 3,
    "subscription": 3, "charge": 2, "pricing": 3, "price": 2, "commission": 3,
}
MEDIUM = {
    "automate": 2, "automation": 2, "business": 2, "workflow": 2, "marketing": 2,
    "funnel": 2, "upsell": 2, "churn": 2, "crm": 2, "ecommerce": 2, "e-commerce": 2,
    "store": 2, "shop": 2, "listing": 2, "seo": 2, "outreach": 2, "retention": 2,
    "bill": 2, "cost": 2, "save": 1, "service": 1,
}
THRESHOLD = 6


def fetch() -> str:
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": "Mozilla/5.0 (money-miner)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def parse(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    items = []
    for it in root.findall(".//item"):
        items.append(
            {
                "title": (it.findtext("title") or "").strip(),
                "description": re.sub(r"\s+", " ", (it.findtext("description") or "").strip()),
                "link": (it.findtext("link") or "").strip(),
                "pubdate": (it.findtext("pubDate") or "").strip(),
            }
        )
    return items


def score(text: str) -> tuple[int, list[str]]:
    t = text.lower()
    hits: list[tuple[int, str]] = []
    for kw, pts in {**STRONG, **MEDIUM}.items():
        if kw in t:
            hits.append((pts, kw))
    hits.sort(reverse=True)
    return sum(p for p, _ in hits), [kw for _, kw in hits[:6]]


def load_seen() -> set[str]:
    if SEEN.exists():
        return set(json.loads(SEEN.read_text()).get("seen", []))
    return set()


def save_seen(seen: set[str]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    SEEN.write_text(json.dumps({"seen": sorted(seen)}, indent=2) + "\n")


def main() -> None:
    xml_text = fetch()
    items = parse(xml_text)
    seen = load_seen()
    fresh = []
    for it in items:
        if not it["link"]:
            continue
        text = f"{it['title']} {it['description']}"
        sc, kws = score(text)
        it["score"] = sc
        it["signals"] = kws
        fresh.append(it)
        seen.add(it["link"])

    fresh.sort(key=lambda x: (-x["score"], x["title"]))
    top = [it for it in fresh if it["score"] >= THRESHOLD][:10]
    save_seen(seen)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    OUT.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# 找赚钱用例日报 {today}",
        "",
        f"扫描 {len(fresh)} 条（其中达标 {len(top)} 条，阈值 {THRESHOLD} 分）",
        "",
    ]
    if top:
        for i, it in enumerate(top, 1):
            lines += [
                f"## {i}. {it['title']}  [{it['score']}]　{it['pubdate']}",
                f"- 信号: {', '.join(it['signals'])}",
                f"- {it['description'][:300]}",
                f"- 链接: {it['link']}",
                "",
            ]
    else:
        lines += [
            "今天没有强赚钱信号（>=6 分）。",
            "",
            "次高 3 条（参考）：",
        ]
        for it in fresh[:3]:
            lines += [f"- [{it['score']}] {it['title']} — {it['link']}", ""]

    md_path = OUT / f"digest-{today}.md"
    md_path.write_text("\n".join(lines) + "\n")
    json_path = OUT / f"digest-{today}.json"
    json_path.write_text(json.dumps({"date": today, "scanned": len(fresh), "top": top}, indent=2, ensure_ascii=False) + "\n")

    # stdout: human+agent readable summary
    print(f"scanned={len(fresh)} qualified={len(top)}")
    print(f"digest={md_path}")
    for it in top:
        print(f"[{it['score']}] {it['title']} | {', '.join(it['signals'][:4])} | {it['link']}")


if __name__ == "__main__":
    main()

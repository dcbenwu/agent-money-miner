#!/usr/bin/env python3
"""WhatsApp / Instagram 获客 campaign 生成器（agent-usecase: 'Build WhatsApp and Instagram outreach campaigns for clients'）

输入：业务 brief JSON（业务名/城市/产品/价格/目标客群/优惠/语气/语言/渠道/触达节奏）
输出：out/{business_slug}/ 下 campaign.md（完整 brief + 消息矩阵 + 合规清单）、messages.csv（可直接粘贴）、plan.json（结构化）

模板兜底 + 可选 LLM 润色（Ollama qwen3.8:27b，超时自动回退模板，绝不硬失败）。
合规内置：WhatsApp 必带 STOP 退订尾行；IG 首条不带外链；附官方限频提示。
"""

from __future__ import annotations

import csv
import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT = BASE / "out"

WHATSAPP_MAX = 320          # chars, 保持短
IG_STAGES = ["opener", "follow_up", "closer"]


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", s.lower()).strip("-")[:40] or "client"


# ---------------- 模板兜底（中英双版） ----------------

TPL = {
    "zh": {
        "whatsapp": {
            "opener": "你好！我是{business}（{city}）的小助理。我们做{product}，现在{promo}，{price}。方便的话我给你发个详情？（回复 STOP 可随时退订）",
            "follow_up": "想再补充一句：{value_prop}。最近不少{target}朋友都问这个，如果你最近刚好有相关需求，回复 1 我发你对比资料。",
            "closer": "这轮的{promo}优惠{deadline}结束。不催你，就是留个最后提醒：{price}，随时回复都行。（回复 STOP 退订）",
        },
        "instagram": {
            "opener": "最近很多{target}都在找靠谱{product}——我们是{city}的{business}，{promo}。有兴趣的话可以看看主页，或直接评论「1」，我把资料发你。",
            "follow_up": "看到你关注这个方向：{value_prop}。想了解我们怎么做到的话，直接问我就行，不群发话术。",
            "closer": "小提醒：{promo}这轮到{deadline}。之后恢复原价{price}。有问题随时问。",
        },
    },
    "en": {
        "whatsapp": {
            "opener": "Hi! I'm from {business} in {city}. We do {product}, and right now {promo} — {price}. Want me to send the details? (Reply STOP to unsubscribe)",
            "follow_up": "Quick add: {value_prop}. Lots of local {target} have asked about this lately — if it fits a need you have, reply 1 and I'll send a comparison sheet.",
            "closer": "This round of the {promo} ends {deadline}. No rush at all — {price}, and I'm here whenever. (Reply STOP to unsubscribe)",
        },
        "instagram": {
            "opener": "Lots of {target} in {city} are asking for a reliable {product} — that's us at {business}, and right now {promo}. Check our profile, or comment “1” and I'll send the details.",
            "follow_up": "Since you follow this space: {value_prop}. Happy to answer how we do it — just ask, no canned replies.",
            "closer": "Heads-up: the {promo} round ends {deadline}. After that it's back to {price}. Any questions, anytime.",
        },
    },
}


def fill(brief: dict, tpl: str, lang: str, channel: str, stage: str) -> str:
    ctx = dict(brief)
    ctx["business"] = brief.get("business_name", "")
    ctx["target"] = brief.get("target_customer", "")
    from collections import defaultdict
    return tpl.format_map(defaultdict(str, **ctx)).replace("  ", " ")


def build_messages(brief: dict) -> list[dict]:
    msgs = []
    for lang in brief["languages"]:
        for channel in brief["channels"]:
            for i, day in enumerate(brief["cadence_days"]):
                stage = IG_STAGES[i] if len(brief["cadence_days"]) == 3 else IG_STAGES[min(i, 2)]
                text = fill(brief, TPL[lang][channel][stage], lang, channel, stage)
                if channel == "whatsapp" and stage in ("opener", "closer"):
                    assert "STOP" in text, "WhatsApp 首条/收尾必须含 STOP 退订行"
                elif channel == "instagram" and stage == "opener":
                    assert not re.search(r"https?://\S+", text), "IG 首条不得带外链"
                msgs.append({"lang": lang, "channel": channel, "day": day, "stage": stage, "message": text})
    return msgs


# ---------------- 可选 LLM 润色 ----------------

def llm_polish(brief: dict, msgs: list[dict], endpoint: str, model: str, timeout: int = 90) -> tuple[list[dict], bool]:
    """让 27B 把模板话术改得更自然。失败/超时 → 原样返回 (msgs, False)。"""
    try:
        prompt = (
            "你是本地小商家的获客文案写手。下面是客户 brief 和一组初稿消息（JSON）。"
            "请把每条 message 改写得自然、口语、不油腻，保留：渠道风格（WhatsApp 简短带 STOP 退订尾行；Instagram 不带外链、不硬广）、"
            "关键事实（业务名/城市/产品/价格/优惠/期限）与语言不变。只输出 JSON 数组，与输入同长度同顺序，"
            "每项只含 message 字段。\n\nBRIEF: " + json.dumps({k: brief[k] for k in ("business_name", "city", "product", "price", "promo", "target_customer", "value_prop")}, ensure_ascii=False)
            + "\n\nMSGS (lang 字段区分语言，按原条目顺序对应): "
            + json.dumps([{"lang": m["lang"], "channel": m["channel"], "stage": m["stage"], "message": m["message"]} for m in msgs], ensure_ascii=False)
        )
        req = urllib.request.Request(
            endpoint + "/api/generate",
            data=json.dumps({"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.7, "num_predict": 3000}}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
        raw = data.get("response", "")
        m = re.search(r"\[.*\]", raw, re.S)
        if not m:
            return msgs, False
        polished = json.loads(m.group(0))
        if len(polished) != len(msgs):
            return msgs, False
        for m_, p in zip(msgs, polished):
            txt = p.get("message", "")
            if not txt:
                continue
            if m_["channel"] == "whatsapp" and "STOP" not in txt:
                txt += " (回复 STOP 退订)"
            m_["message"] = txt[:WHATSAPP_MAX + 40]
        return msgs, True
    except Exception as e:
        print(f"[polish] 跳过 LLM 润色: {type(e).__name__}: {e}", file=sys.stderr)
        return msgs, False


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    brief_path = Path(sys.argv[1])
    brief = json.loads(brief_path.read_text())
    polished = brief.get("polish", True)

    msgs = build_messages(brief)
    if polished:
        endpoint, model = brief.get("llm", {}).get("endpoint", "http://192.168.50.33:11434"), brief.get("llm", {}).get("model", "qwen3.8:27b")
        msgs, used_llm = llm_polish(brief, msgs, endpoint, model)
    else:
        used_llm = False

    slug = slugify(brief["business_name"])
    out_dir = OUT / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    # messages.csv
    with open(out_dir / "messages.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["lang", "channel", "day", "stage", "message"])
        w.writeheader()
        w.writerows(msgs)

    # plan.json
    plan = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "brief": brief,
        "used_llm_polish": used_llm,
        "messages": msgs,
    }
    (out_dir / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n")

    # campaign.md
    lines = [
        f"# Campaign Brief — {brief['business_name']}（{brief['city']}）",
        "",
        f"生成: {plan['generated_at']}　模式: {'模板 + LLM 润色' if used_llm else '纯模板（LLM 不可达，降级运行）'}",
        "",
        "## 定位",
        f"- 目标客群: {brief['target_customer']}",
        f"- 核心卖点: {brief['value_prop']}",
        f"- 钩子: {brief['promo']}",
        f"- 价格: {brief['price']}",
        f"- 触达节奏: 第 " + " / ".join(str(d) for d in brief["cadence_days"]) + " 天（开场 → 跟进 → 收尾）",
        "",
        "## 消息矩阵",
        "",
        "| 渠道 | 天 | 阶段 | 语言 | 消息 |",
        "|---|---|---|---|---|",
    ]
    for m in msgs:
        cell = m["message"].replace("\n", " ").replace("|", "\\|")
        lines.append(f"| {m['channel']} | D{m['day']} | {m['stage']} | {m['lang']} | {cell} |")
    lines += [
        "",
        "## 合规与限频（必守）",
        "- WhatsApp Business：仅向已同意营销的联系人发送；每条必须可 STOP 退订；官方模板消息限频（起步 ~25~250/天，随信誉上调），不要群发轰炸",
        "- Instagram：禁用非官方自动化 DM；首条不带外链（封号高危）；用评论「1」引导双向对话",
        "- 通用：同一用户 24h 内最多 1 条；对方 48h 无回应即停；禁止编造限时优惠",
        "",
        "## 交付物",
        "- `messages.csv` — 可直接粘贴的成稿（含语言/渠道/天/阶段）",
        "- `plan.json` — 结构化计划（可被 agent 消费）",
    ]
    (out_dir / "campaign.md").write_text("\n".join(lines) + "\n")

    print(f"OK out={out_dir} msgs={len(msgs)} llm='{used_llm}'")
    for m in msgs[:4]:
        print(f"  [{m['lang']}/{m['channel']}/D{m['day']}/{m['stage']}] {m['message'][:80]}...")


if __name__ == "__main__":
    main()

# agent-money-miner

每天从 [agentusecases.ai](https://agentusecases.ai/) 挖"能赚钱的 AI agent 用例"，打分排序推 Telegram；老板点中哪个，空闲时间就去搭 demo。

**立项章程 / 打分口径 / 验收：[PROJECT.md](PROJECT.md)**

## 跑法

```bash
python3 scan.py          # 抓取+打分+出 digest（out/digest-*.md）
bash run_daily.sh        # cron 入口（每日 09:05 北京时间）
```

产物：`state/seen.json`（去重）、`state/backlog.md`（待实现清单）、`out/digest-*.md|.json`。

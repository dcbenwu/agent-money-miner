# agent-money-miner（找赚钱用例挖矿项目）

> 一句话：**每天自动从 [agentusecases.ai](https://agentusecases.ai/) 挖出"能用来赚钱"的 AI agent 用例，排好优先级推给老板；老板拍板哪个值得做，空闲时间我就去把它搭出来。**

## 数据源

- agentusecases.ai：每日聚合的"真实人在用 AI agent 做什么"，1700+ 用例、每天 ~20 条新增，带原始 prompt 与出处（HN/Reddit/X/dev.to）
- 机器可读端点：`https://agentusecases.ai/feed.xml`（RSS，~60 条滚动窗口）
- 分类里 Money/Bills & Benefits 133 条、Work & Operations 300 条是主要富矿

## 管线（已跑通 v1）

```
feed.xml (RSS)
  → scan.py：解析 → 按 money 信号打分（强/中/弱关键词加权）→ 去重（state/seen.json）
  → out/digest-YYYY-MM-DD.md + .json：Top N 机会（标题/信号/链接/日期）
  → Telegram 推送（cron，每日 09:05 北京时间）
  → 老板点哪个 → 进 state/backlog.md，空闲时段实现（"做完"才算数）
```

## 文件

| 文件 | 说明 |
|---|---|
| `scan.py` | 抓取+打分+去重+出 digest（纯 Python 标准库，无依赖，Mac 本地跑） |
| `run_daily.sh` | cron 入口：跑 scan.py 并打印当日 digest 路径 |
| `state/seen.json` | 已扫用例去重表（按链接） |
| `state/backlog.md` | 老板选中、待空闲实现的用例（人工维护） |
| `out/digest-*.md/.json` | 每日产出 |

## 打分口径（v1，可迭代）

- **强信号（3 分）**：refund / unclaimed / negotiate / discount / invoice / tax / sell / revenue / monetiz / income / client / lead / agency / outsource / dropship / arbitrage / resell / affiliate / freelance / subscription
- **中信号（2 分）**：automate / business / workflow / marketing / funnel / upsell / churn / CRM / e-commerce / store / shop / listing / SEO / outreach / pricing
- 取分 >=6 为"值得看"，其余当日只留档不推
- 迭代方向：接入 LLM 二次排序、按"我们能不能做"（Mac+udoge 资产匹配度）打第二维分

## 验收

- v1：**cron 每日产出 digest 并推 Telegram**；无强信号的日子要明说（不编）
- v1.5：老板选中 1 个用例 → backlog 有记录 → 空闲时段实现一个可跑 demo 并发他过审
- v2：打分加入"我们资产匹配度"（我们有什么、缺什么、能不能 3 天内跑出 demo）

## 不做

- 不注册付费服务/不付费订阅数据源
- 不代发任何对外消息（推送只到老板的 Telegram）
- 用例网站来源只读，不改

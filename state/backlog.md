# 空闲实现 backlog（老板拍板后进这里）

> 流程：每日 digest 推老板 → 老板说"做 X" → 抄到这里 → 空闲时段实现 demo → 发过审 → 移入 PROJECT.md 验收记录。

## 待实现

- （等 digest 首推后由老板点名）

## 已交付待审（2026-10-30，老板拍板"好"后开工）

- **[8 分] Build WhatsApp and Instagram outreach campaigns for clients** → `demos/whatsapp-ig-campaign/`
  - 输入业务 brief JSON → 输出 campaign.md（定位/消息矩阵/合规清单）+ messages.csv（可粘贴成稿）+ plan.json
  - 模板兜底 + udoge 27B 润色（离线自动降级）；合规硬断言：WA 首条/收尾必带 STOP、IG 首条禁外链
  - 样例成稿（山雾咖啡烘焙）：`demos/whatsapp-ig-campaign/out/山雾咖啡烘焙/campaign.md`
  - 已知小瑕疵：英文版被 27B 混进了中文 STOP 尾行（可迭代：润色后按语言回填语言匹配的退订句）

# V2C 中文写作流程验收报告

日期：2026-08-27
状态：Windows 本地低 Token 验收通过

## 本次验收范围

原计划的 8–12 篇材料、4000–6000 字中文稿属于真实研究规模。根据用户后续授权，本次改为系统 tracer bullet：

- 只使用 3 篇已核验材料；
- 中文论证稿控制在约 2000 字；
- 目标是检验技能边界、状态恢复、证据追踪和审计闭环，不主张形成可投稿研究；
- 英文对齐能力继续保留为独立 capability，但本次中文验收不调用它。

这一缩减显著降低了检索、阅读和生成成本，同时仍覆盖所有关键接口。

## 实际运行

- 项目：`gsma-sentiment-engagement`
- 运行 ID：`run-20260827T082207Z-46473581`
- 最终检查点：`20260827T084945Z_15307624`
- 检查点验证：`verified`，状态哈希匹配，16 个输入/输出产物哈希全部匹配，未解决 gate 为 0。
- 完成顺序：论证架构 → 中文起草 → 引文复核 → 文风审计 → 约束修订 → 内部修订审计 → 模拟匿名审稿。

主要产物：

- `projects/gsma-sentiment-engagement/writing/chinese-research-note.md`
- `projects/gsma-sentiment-engagement/writing/revised-chinese-research-note.md`
- `projects/gsma-sentiment-engagement/writing/citation-regression.json`
- `projects/gsma-sentiment-engagement/writing/prose-style-report.json`
- `projects/gsma-sentiment-engagement/writing/revision-audit.md`
- `projects/gsma-sentiment-engagement/writing/peer-review.md`

文风报告记录 2353 个非空白字符、19 段、58 句、0 个公式化填充表达、0 个重复段首，五个保护锚点全部保留。唯一提示是作者名和机制说明的重复 n-gram，属于 advisory，不触发机械改写。

## 理论决策结论

`theory-decision-packet.json` 中的 `selected` 状态来自用户本人在另一段对话中的明确授权，因此该决策有效。此前把它判断为越权，是因为审查时没有看到完整授权上下文；本次已通过接受漂移流程登记为人工编辑并重新建立可信检查点。

当前仍有一个表达层问题：理论选择存在于可验证产物及其 `user-decision:gsma-theory-selected-20260827` 溯源中，但项目事件流只记录了早期系统建议和接受漂移操作。下一版应增加不可变的用户理论选择事件，使“建议 → 用户选择”的时间线无需依赖多个文件共同解释。

## 真实运行暴露并修复的问题

1. 在终点接受人工漂移后，运行会停留在 `running` 且没有下一节点。现在只有 `accept_drift` 的终点恢复会自动完成；普通交互式 `continue` 仍保留原语义。
2. 新写作 capability 缺少内核 gate evaluator，合法产物仍会被阻塞。现在六类写作/审计 capability 均有确定性 gate。
3. 同一 workflow 两次调用 `ssci-section-drafting` 时，内核按 capability ID 合并节点。现在重复 capability 使用 workflow node ID 记录完成状态，并按节点解析前驱和输入输出。
4. 文风审计声明保护锚点，却没有接收包含锚点的 `draft_trace`。映射和 capability 输入声明已补齐。
5. gate 状态存在两类污染：新运行继承旧运行 gate；同一运行中已经由通过结果覆盖的早期失败仍出现在最终检查点。现在新运行重置物化 gate 状态，检查点只列最新仍失败的 gate；完整历史仍保留在 append-only 事件日志中。

所有修复均有先失败、后通过的回归测试。

## 安装与源码溯源判断

- Windows PowerShell 5.1 安装器路径修复有必要保留。参数默认表达式中 `$PSScriptRoot` 可能为空，把脚本相对路径解析移入函数体可以避免真实安装失败。本次以原生 Windows PowerShell 5.1 执行 `-WhatIf`，12 个 Skill 均返回 `unchanged`；不需要继续修改。
- 恢复 `theory-architecture` 的 `SOURCE_MANIFEST` 文件级记录是正确决定。它补回来源文件、复用方式、修改、许可、安全和测试链，不增加运行时 token 成本。
- 当前机器安装记录包含 12 个 Research Skills OS Skill；七个原有 `ssci-*` Skill 仍不在安装器目标中，没有被覆盖。

## 验证证据

- 关键状态、检查点、生命周期、七节点 workflow 与 GSMA 验收：`52 passed`。
- 全套测试：`421 passed, 1 skipped in 47.86s`。
- 最终覆盖率测试：`421 passed, 1 skipped in 86.14s`，总覆盖率 `93.92%`（门槛 `90%`）。
- Ruff 检查通过，`src/tests` 的 201 个文件格式检查通过；mypy 对 75 个源文件无问题；`git diff --check` 通过。

## 下一轮改进顺序

1. 增加不可变的理论选择事件和决策时间线产物。
2. 在 workflow schema 中直接声明每个节点的输入输出，而不是从 artifact mapping 推导重复 capability 的节点合同。
3. 对同一 `uncertainty_id` 做项目状态去重，避免跨节点重复展示。
4. 增加作者—年份显示层，在后台保留 Evidence ID。
5. 让文风重复检测报告具体位置，并排除标题、引文标识等结构性重复。
6. 增加项目 registry snapshot 的原子升级命令；验收测试按 request/run 定位检查点，而不是依赖全局 current pointer。

在系统测试目的不变的前提下，不建议继续增加文献数量。只有转入真实研究时，才需要扩大文献覆盖并执行 GSMA 数据诊断与统计分析。

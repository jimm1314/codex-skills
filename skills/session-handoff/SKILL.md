---
name: session-handoff
description: 安全收尾当前代码项目 Session，并创建、更新、压缩本地 CODEX_HANDOFF.md 状态快照。用户明确要求“结束/切换 Session”“生成交接”“更新 handoff”“给下一个 Codex 留状态”时使用；只检查项目和 Git 状态、维护交接文件及必要的 .git/info/exclude，不修改业务代码，不负责 Session Resume，也不执行 commit、push、merge、rebase、reset、fetch 或 pull。
---

# Session Handoff

## 职责边界

此 Skill 只负责 Session 收尾：

- 检查当前真实项目与 Git 状态；
- 整理仍有效的工作结论；
- 创建或重写 `CODEX_HANDOFF.md`；
- 删除其中过期、重复和流水账信息；
- 检查敏感信息与本地 Git 排除；
- 留下下一 Session 的明确下一步。

不继续业务开发，不修 Bug，不重构，不提交或同步代码。只有用户明确要求维护交接时才允许写入 Handoff。

## 事实优先级

```text
当前真实源码 / Git > CODEX_HANDOFF.md > 历史对话或 Skill 假设
```

旧 Handoff 和聊天记录只能作为线索。发生冲突时以 Git 和相关源码为准，并删除失效描述。

## 收尾检查

先执行只读检查：

```text
git branch --show-current
git status
git diff --stat
git diff
git log --oneline --decorate -5
```

按需检查当前任务相关的少量配置、测试和运行结果。不要递归扫描整个仓库，不要为了写 Handoff 重新理解完整项目。

同时确认：

- 当前 HEAD 和关键本地 commit；
- staged、unstaged、untracked 和 ignored 产物；
- 是否存在 merge/rebase/cherry-pick 等进行中状态；
- 当前分支与已知上游关系；
- 本 Session 的验证结论及尚未验证项。

## 更新方式

如果 `CODEX_HANDOFF.md` 不存在则创建；存在则整体整理，不在末尾无限追加历史。

至少包含：

1. 当前目标；
2. Git 状态；
3. 已完成工作；
4. 关键文件及其作用、状态和后续关注点；
5. 关键设计决定与不容易从源码看出的约束；
6. 已验证内容；
7. 已知问题和风险；
8. 已排除方案的最终结论；
9. 按优先级排列的下一步；
10. 新 Session 接手指南。

只保留当前仍有效的状态。不要复制完整源码、diff、长日志、聊天历史或可以随时从 Git 获取的大量信息。

目标长度约 2,000～6,000 tokens；明显超过约 8,000 tokens 时重新压缩。

## 新 Session 接手指南

Handoff 中固定保留以下短流程：

1. 先读 `CODEX_HANDOFF.md`；
2. 检查 branch；
3. 执行 `git status`；
4. 查看最近 `git log`；
5. 有未提交修改时再查看 `git diff`；
6. 根据“下一步”和“关键文件”按需读源码；
7. 信息不足时逐步扩大；
8. Handoff 与真实状态冲突时以源码和 Git 为准；
9. 确认状态后再修改代码。

## 敏感信息

禁止写入：

- API Key、Access Token、Secret、密码；
- Cookie、SSH 私钥、认证头；
- `.env` 的具体值；
- 公司内部认证凭据或含凭据 URL。

只记录变量名和用途。完成后使用本地模式检查常见密钥、私钥、JWT 和凭据赋值；发现疑似值时停止并移除或请用户确认，不在回复中重复敏感内容。

## 本地 Git 排除

`CODEX_HANDOFF.md` 只用于本地 AI 交接：

1. 不修改项目正式 `.gitignore`。
2. 检查 `.git/info/exclude` 是否已有精确行 `CODEX_HANDOFF.md`；没有时才加入。
3. 如果 Handoff 已被 Git 跟踪，不自行删除、untrack、reset 或改写 Git 历史，直接报告用户。
4. 不把其他业务文件顺便加入排除。

## 允许与禁止

本 Skill 允许修改：

- `CODEX_HANDOFF.md`
- 必要时的 `.git/info/exclude`

禁止修改：

- Skill、业务代码、测试、配置和项目文档；
- `.gitignore`；
- Git index、commit、branch 或远端状态。

禁止执行 commit、push、merge、rebase、reset、fetch、pull、clean 或删除代码。

## 完成验证

完成后确认：

- Handoff 已创建或更新；
- 文件未被 Git 跟踪且已被本地 exclude 命中，或已报告异常；
- tracked working tree 未因本次交接发生变化；
- 未发现敏感值；
- 下一步明确且没有继续业务开发。

最终只汇报：Handoff 状态、主要内容、本地排除、Git 工作区、敏感信息检查和下一步，然后停止。

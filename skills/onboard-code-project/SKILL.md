---
name: onboard-code-project
description: 兼容旧入口：当用户明确调用 onboard-code-project，或要求零基础理解并首次运行代码项目时，将任务路由到 take-over-code-project 的“首次 Onboarding”模式。已有 CODEX_HANDOFF.md、继续旧 Session、追踪功能或准备开发时，不使用此兼容 Skill。
---

# 项目 Onboarding 兼容入口

此 Skill 暂时保留旧名称，避免已有调用立即失效；完整流程只维护一份。

1. 读取 `../take-over-code-project/SKILL.md`。
2. 使用其中的“首次 Onboarding”模式，并按需读取：

   ```text
   ../take-over-code-project/references/first-onboarding.md
   ```

3. 如果项目存在 `CODEX_HANDOFF.md`，不要重新做首次项目地图，改用同一 Skill 的 Session Resume 模式。
4. 不在本文件复制项目分析、环境安装、Git 或 Session 规则。
5. 用户进入代码实现、Git 操作或 Session 收尾时，按主 Skill 的职责边界路由。

待新入口稳定后，可以在用户明确确认下删除这个兼容 Skill。

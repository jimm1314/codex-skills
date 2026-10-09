# codex-skills

我的 [Codex CLI](https://github.com/openai/codex) 技能（skills）与 `AGENTS.md` 配置快照。

这个仓库的用途：**换机器 / 重装环境时一键还原完整的 Codex 能力**，同时用 Git 留存技能的历史版本。

- 快照来源：`~/.codex/skills/`（其中 `lark-*` 原为指向 `~/.agents/skills/` 的软链，入库时已解引用为实体文件）
- 快照时间：2026-10-09

---

## 目录结构

```
.
├── AGENTS.md                  # 全局指令（来自 ~/.codex/AGENTS.md）
├── install.sh                 # 安全还原脚本：把 skills/ 软链回 ~/.codex/skills/
├── README.md
└── skills/
    ├── agent-reach/                       # 第三方
    ├── analyze-llm-evaluation-results/    # 自研
    ├── design-llm-test-cases/             # 自研
    ├── engineer-code-safely/              # 自研
    ├── guide-gitlab-safely/               # 自研
    ├── lark-doc/                          # 第三方（larksuite/cli）
    ├── lark-drive/                        # 第三方（larksuite/cli）
    ├── lark-markdown/                     # 第三方（larksuite/cli）
    ├── lark-shared/                       # 第三方（larksuite/cli）
    ├── onboard-code-project/              # 自研（兼容旧入口）
    ├── saas-bench-runner/                 # 自研（含 scripts / tests）
    ├── session-handoff/                   # 自研
    ├── stepcode-fb/                       # 由 StepCode 自动生成
    ├── take-over-code-project/            # 自研
    ├── ui-ux-pro-max/                     # 第三方
    └── .system/                           # Codex 内置，随版本自动管理
        ├── imagegen/
        ├── openai-docs/
        ├── review-agent/
        ├── skill-creator/
        └── skill-installer/
```

---

## 技能清单

### 自研流程技能

围绕「安全地接手项目 → 推进开发 → 交接收尾」的完整工作流，以及 LLM 测评相关能力。

| 技能 | 用途 |
| --- | --- |
| `engineer-code-safely` | 证据优先地实现、修改、修复、重构和审查代码；覆盖需求澄清、接口契约、计划、编码、系统化调试、测试、代码审计与交付 |
| `take-over-code-project` | 首次接管或在新 Session 恢复代码项目：优先读 `CODEX_HANDOFF.md` 并用真实 Git / 源码验证，建立项目地图、准备启动环境、追踪功能与 Bug 的调用链 |
| `onboard-code-project` | 兼容旧入口，把「零基础理解并首次运行项目」路由到 `take-over-code-project` 的首次 Onboarding 模式 |
| `session-handoff` | 安全收尾 Session，创建 / 更新 / 压缩 `CODEX_HANDOFF.md` 状态快照；只维护交接文件，不碰业务代码，不执行 Git 写操作 |
| `guide-gitlab-safely` | 零基础友好的中文 Git / GitLab 协作：branch、status、diff、fetch、pull、commit、push、merge、rebase、冲突与回滚，写操作按风险说明并取得授权 |
| `design-llm-test-cases` | 设计可执行、可评分、可追踪、可归因的 LLM 测试用例：Rubric、覆盖率矩阵、人工测试表、自动化测试集、失败归因方案 |
| `analyze-llm-evaluation-results` | 分析 LLM 测评结果：数据质量检查、总体与分维度指标、模型 / Prompt / 参数对比、回归与失败模式、LLM-as-a-Judge 一致性、测评结论与修复建议 |
| `saas-bench-runner` | 安全地 preflight / 启动 / 监控 / 恢复 / 汇总 / 对比 SaaS-Bench 评测（原生与 Harbor adapter 两种模式），含 `scripts/` 与 `tests/` |
| `stepcode-fb` | 由 StepCode 自动生成：导出当前 session 并打印反馈 session ID |

### 第三方技能

以下技能由上游仓库安装而来，**版权归原作者**，此处仅作本机快照留存。如需更新，请从原始来源重新安装，不要以本仓库为准。

| 技能 | 来源 | 说明 |
| --- | --- | --- |
| `agent-reach` | [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach) | 互联网内容路由：16 个平台（小红书 / Twitter / B站 / Reddit / LinkedIn / Boss直聘 / YouTube / 雪球 / RSS 等），多后端路由（OpenCLI / 各平台 CLI / API） |
| `ui-ux-pro-max` | 社区技能（本机安装，未记录上游 commit） | UI/UX 设计智能：79 种风格、192 组产品配色、74 组字体搭配、119 条 UX 规范、105 个图标、25 种图表、22 个技术栈；含本地可检索数据与脚本 |
| `lark-doc` | [larksuite/cli](https://github.com/larksuite/cli) | 飞书云文档（Docx / Wiki）读取、创建、编辑，插入或下载图片附件，思维笔记 |
| `lark-drive` | [larksuite/cli](https://github.com/larksuite/cli) | 飞书云空间：上传 / 下载、文件夹管理、权限与评论、密级标签、本地文件导入为飞书文档 |
| `lark-markdown` | [larksuite/cli](https://github.com/larksuite/cli) | 飞书原生 Markdown 文件的查看、创建、上传、编辑与版本比较 |
| `lark-shared` | [larksuite/cli](https://github.com/larksuite/cli) | lark-cli 的登录 / 身份 / 权限 / 安全规则处理 |

> `ui-ux-pro-max` 的 `data/` 目录内保留了 `data-provenance.json`、`google-font-licenses.json` 等上游数据文件，字体与图标数据的授权信息以这些文件为准。

### Codex 内置技能（`.system/`）

随 Codex 版本自动分发和更新，**收录在此仅为完整快照**。还原时若本机 Codex 已自带，`install.sh` 会自动跳过，避免覆盖新版本。

| 技能 | 用途 |
| --- | --- |
| `imagegen` | 生成或编辑位图，如照片、插画、贴图、精灵图、模型稿 |
| `openai-docs` | Codex 模型 / 定价 / 定时任务 / 技能 / 设置 / 排障 / 自定义等自助查询 |
| `review-agent` | 对指定代码变更做只读、缺陷优先的评审，返回全部可执行发现 |
| `skill-creator` | 创建或更新 Codex 技能及其配套资源 |
| `skill-installer` | 从精选列表或 GitHub 仓库路径安装技能到 `$CODEX_HOME/skills` |

---

## AGENTS.md

根目录的 `AGENTS.md` 是本机 `~/.codex/AGENTS.md` 的副本，与 `~/.claude/CLAUDE.md` 内容完全一致，包含两段全局规则：

1. **任务启动与技能选择** —— 先判断目标、授权与歧义，再选技能；复杂任务先做只读检查并说明计划；已明确授权的任务直接执行，不重复确认。
2. **飞书工作文档工作流** —— 记录 / 整理 / 总结工作时，用 `lark-doc` 维护一个长期工作文档，`lark-drive` 定位文件，`lark-shared` 处理登录授权；默认不新建多个文档，改动前先读最小必要范围、窄范围更新后回读验证。

> 另有 `~/AGENTS.md`（1701 字节），内容是上述第 2 段的子集，本仓库只保留内容更全的版本。

---

## 安装 / 还原

```bash
git clone https://github.com/jimm1314/codex-skills.git
cd codex-skills
./install.sh
```

`install.sh` 的行为：

- 把 `skills/` 下的每个技能**软链**到 `$CODEX_HOME/skills/`（默认 `~/.codex/skills`），因此 `git pull` 后技能自动更新
- 目标已存在时**跳过并打印提示**，绝不覆盖
- `.system/` 单独处理：Codex 已自带则跳过
- 不修改任何现有文件，不执行删除操作

手动方式（等价）：

```bash
ln -s "$PWD/skills/take-over-code-project" ~/.codex/skills/
```

若想让 Claude Code 也能用同一批技能，把软链指向本仓库即可：

```bash
ln -s "$PWD/skills/engineer-code-safely" ~/.claude/skills/
```

---

## 更新本仓库

在本机改了技能之后：

```bash
cd ~/codex-skills
rsync -aL --exclude '.DS_Store' --exclude '__pycache__' --exclude '*.pyc' ~/.codex/skills/ skills/
git add -A && git commit -m "sync: update skills" && git push
```

> 注意：`lark-*` 在本机是指向 `~/.agents/skills/` 的软链，`rsync -aL` 会跟随后解引用为实体文件，这是刻意的——保证仓库自包含。

---

## 安全说明

入库前已扫描高置信密钥模式（`sk-*`、`ghp_*`、`github_pat_*`、AWS AKIA、PEM 私钥、Slack token 等），未发现真实凭据。以下内容**刻意未纳入**本仓库：

- `~/.codex/auth.json`、`config.toml` 等含认证与个人配置的文件
- 会话历史、日志、数据库、memories
- 任何 `.env` 与本地环境变量文件

若后续在本机新增技能，提交前请重复一次密钥扫描。

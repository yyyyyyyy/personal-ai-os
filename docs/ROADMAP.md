# 改进路线图

> 一次全角度项目体检的结论与可执行清单。日期：2026-06-13，版本基线 v0.9.0。
> 本文回答「下一步把精力投在哪」；通用工作方式见 [POSTMORTEM.md](POSTMORTEM.md)，执行清单见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 整体判断

工程底子扎实——事件溯源 + Kernel 边界守卫、完整威胁模型、SSRF/taint/capability 多层防御、CI 多重门禁、经验沉淀（POSTMORTEM）。**"让项目更好"的关键不是再堆技术，而是补齐几处真实短板，并把底座转化为被验证的用户价值。**

- 规模：~12.8k 行 Python + ~7k 行 TS，43 次提交
- 阶段：底座聚焦 + 用户验证（见 [USER_VALIDATION.md](USER_VALIDATION.md)），目标 D7 留存 ≥ 40%
- 测试：46 个后端测试文件 + 15 个前端测试

## 各角度诊断

| 角度 | 现状 | 评级 | 杠杆 |
|------|------|:---:|------|
| 安全 | 威胁模型 + SSRF + taint + capability 审批，安全审查 0 漏洞 | 🟢 | 已是护城河，保持 |
| 架构 | 事件溯源 + Kernel 边界，可重建 / 可无损导出 | 🟢 | 优秀，控制复杂度增长 |
| 类型 / 测试门禁 | mypy 仅覆盖部分模块（CI 注明 legacy type debt），coverage 仅 `app/core/runtime`，门禁 65% | 🟡 | 渐进扩面 |
| 复杂度热点 | `kernel.py` 905 行、`projectors.py` 577、`mcp_hub.py` 556、`brain.py` 509 | 🟡 | 按职责拆分 |
| 数据路径 | 存在 `backend/backend/data/` 幽灵数据库，正是 README FAQ 警告的反模式 | 🔴 | 立即清理 + 加防护 |
| 产品验证 | 有招募计划与留存指标，但缺真实用户数据闭环 | 🔴 | **最高杠杆** |
| 可观测性 | 有 telemetry / egress 审计，缺统一错误监控与启动健康自检 | 🟡 | 中期补 |

## P0 — 立即（低成本高收益）

### P0-1 清理幽灵数据库并加路径防护

- **问题**：`backend/backend/data/personal_ai.db` 存在且仍在被写入（最近一次为本次体检当天）。该目录已被 `.gitignore` 忽略，但数据被写到错误位置会造成"数据丢失"假象。
- **影响**：对一个主打**数据主权**的项目，这是致命的信任体验问题。
- **根因方向**：某进程在 `backend/` 工作目录下以相对路径解析 `backend/data`，叠加成 `backend/backend/data`。`app/config.py` 默认用绝对 `BASE_DIR`（正确），需排查是否有脚本 / 旧命令绕过了它。
- **建议**：
  - 删除 `backend/backend/` 目录。
  - 启动时（`config.py` 或 `main.py`）记录解析后的绝对 `data_dir`，并在路径中检测到重复 `backend/backend` 时 `logger.warning` 或直接断言。
- **验收**：重跑全部 verify 脚本与 `make ci-local` 后，不再生成 `backend/backend/`。

### P0-2 修补 `.env*` 同目录保护盲点

- **问题**：`apply_patch` 的 `_is_env_secret_file`（`backend/app/core/harness/mcp_servers/filesystem.py`）要求 `p.parent == prot.parent`，导致子目录下的 `.env.local` 等变体不被默认 `.env` 保护规则拦截，与 `brain.py` system prompt 中「所有 .env* 变体均受保护」的叙事不一致。
- **建议**：放宽匹配，使任意目录下的 `.env` / `.env.*`（放行 `.env.example`）都受保护；补单测覆盖子目录 case。
- **验收**：新增测试断言 `backend/.env.local` 被拒、`.env.example` 放行。

## P1 — 短期（还技术债）

### P1-1 mypy 与 coverage 门禁分阶段扩面

- **问题**：mypy 仅覆盖 runtime / 部分 agents / product / api；coverage 仅统计 `app/core/runtime`，门禁 65%。其余模块为类型与覆盖盲区。
- **建议**：每次纳入**一个**模块并同步补测 / 补类型，避免一次性打挂门禁（见 POSTMORTEM 模式 5 与「扩大 CI 门禁前先量一下」）。
- **验收**：每轮 PR 让 mypy / coverage 覆盖范围净增一个模块且门禁不降。

### P1-2 拆分复杂度热点

- **问题**：`kernel.py`(905) / `projectors.py`(577) / `mcp_hub.py`(556) / `brain.py`(509) 体量偏大。
- **建议**：优先拆 `kernel.py`，按 Event Log / State / Permissions 三职责拆成子模块或 Mixin，并用 Protocol 向 mypy 声明宿主属性（见 POSTMORTEM「Python mixin 触发 mypy attr-defined」）。
- **验收**：拆分后边界守卫 + 重建验证 + 全量测试通过，单文件控制在合理行数。

## P2 — 中期（产品价值）

### P2-1 启动真实用户验证（最高 ROI）

- **理由**：底座已足够，继续打磨边际收益递减。哪怕 5 个用户连续使用 2 周，拿到 D7 数据，价值高于再加若干工具。
- **建议**：按 `USER_VALIDATION.md` 招募 5–20 人，埋点 D7 留存 / 导出使用率 / 主动对话天数，按其中的决策规则收敛或深化。

### P2-2 围绕尖刀场景做体验闭环

- **建议**：在收件箱（最具差异化）等单一场景做端到端打磨——分类准确率、摘要质量、对话内查信顺滑度，形成可被用户感知的"一件事做到极致"。

### P2-3 补统一可观测性

- **建议**：统一错误捕获与启动健康自检（依赖、迁移、数据目录、外部 MCP 连通性），降低自托管用户的排障成本。

## 优先级速览

| 优先级 | 行动 | 类型 | 成本 |
|:---:|------|------|:---:|
| P0-1 | 清理幽灵数据库 + 路径防护 | 修复 | 低 |
| P0-2 | `.env*` 保护盲点 | 安全 | 低 |
| P1-1 | mypy / coverage 分阶段扩面 | 技术债 | 中 |
| P1-2 | 拆分 `kernel.py` 等热点 | 重构 | 中 |
| P2-1 | 启动真实用户验证 | 产品 | 中 |
| P2-2 | 尖刀场景体验闭环 | 产品 | 中高 |
| P2-3 | 统一可观测性 | 运维 | 中 |

## 建议节奏

1. ~~先清 P0（一次提交即可，立刻消除信任与安全隐患）。~~ ✅ 2026-06-13
2. P1 与 P2-1 并行：还债的同时启动用户招募——验证数据回来前不要过度投入新功能。
3. 依据 `USER_VALIDATION.md` 的 D7 数据，再决定深化哪个尖刀场景（P2-2）。

## 实施记录（2026-06-13）

| 项 | 状态 | 说明 |
|:---|:---:|:---|
| P0-1 幽灵数据库 + 路径防护 | ✅ | `resolve_project_path` 相对路径锚定 repo root；`.env.example` 移除易误导的相对路径；启动日志 + `startup_health` |
| P0-2 `.env*` 保护 | ✅ | 任意目录 `.env` / `.env.*` 拦截，`.env.example` 放行 |
| P1-1 mypy/coverage 扩面 | ✅ | 纳入 `app/core/harness/` |
| P1-2 拆分 kernel.py | ✅ | 抽出 `kernel_query_state.py`（QueryStateMixin） |
| P2-1 用户验证埋点 | ✅ | `/api/system/validation-metrics` + `validation_metrics.py` |
| P2-2 收件箱体验闭环 | ⏳ | 待用户验证数据后再深化 |
| P2-3 启动健康自检 | ✅ | `startup_health.py` + `/api/system/health` 扩展 |

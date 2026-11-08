# 本机 DSH Media Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. 本任务为已获授权的本机配置实施；沿用现有会话执行，不提交仓库代码。

**Goal:** 创建独立 media Web profile，接入 ComfyUI、SpeechRail、ImageHive 和 FFmpeg，并隔离通用 profile 的影音工具。

**Architecture:** 使用已安装的 dsh-base / dsh-web-app；工具通过官方 MCP client 与既有服务连接。独立 media preset 承载创作规则、专用技能和工具发现；模型路由沿用现有本机配置，服务生命周期仍由原应用持有。

**Tech Stack:** DSH 0.2.1-rc.2、Comfy MCP、SpeechRail MCP、ImageHive MCP、FFmpeg、YAML。

**Spec:** 当前用户授权及本会话可行性分析；最终定制方案见 CUSTOMIZATION.md。

## Global Constraints

- 先保留逐文件原始备份与 SHA-256；现有未知配置和用户数据不覆盖。
- 不修改 dsh 源码，不下载模型，不重启或卸载现有推理服务，不清理队列。
- 配置和备份包含既有路由信息，目录权限 0700、敏感文件 0600；验收报告不含凭据。
- 长渲染异步提交并记录 prompt_id；工具超时不代表任务失败，不自动重投。
- profile 隔离工具注册，不声称隔离共享 GPU、文件或服务队列。

## Review Focus

- 通用 profile 新会话仍能发现影音工具：检查实际注册集合和生图 bundle。
- media 使用错误模型目录或另起服务：复用本机 MCP 绝对路径，核查运行态。
- MCP 协议兼容或 stdio 环境缺失：使用现有 ImageHive adapter，验证三个服务调用。
- 配置重载覆盖既有状态或运行任务：比较输入哈希，只做必要最小编辑；不强制重启 Desktop。
- 验收误称生产质量或持久恢复：分开记录注册、只读调用、FFmpeg 媒体处理和未执行生成项。

## Task 1: 独立 profile 与创作规则

- [x] 备份各 profile manifest、patch、lockfile 和全局 patch，记录 SHA-256。
- [x] 创建 media manifest、patch、独立 preset、专用技能与深度定制方案。
- [x] 使用 dsh --profile media --dump-config 检查最终组合。

## Task 2: 通用工具分离

- [x] 从 Desktop patch 移除 SpeechRail / ImageHive / image-gen 行，从 bundles 移除 dsh-image-gen；保留原依赖制品以便回退。
- [x] 对比其余行、模型路由和全局配置，确保未改。
- [x] 用通用配置启动独立验收实例检查影音工具不可见。

## Task 3: 必要验收与交付

- [x] media 实际启动；三个 MCP 工具可发现且各完成一次无副作用调用。
- [x] FFmpeg 生成合成测试片，FFprobe 核对时长、尺寸与音轨；拒绝覆盖已有输出。
- [x] 验证 media 专用技能可发现、模型选择可见、Web 及浏览器界面；未发送模型请求。
- [x] 验证回退备份哈希，提供受哈希保护的恢复脚本与验收报告。
- [x] 独立只读审查 media 完成，图像输入能力文案已收窄。

## 完成记录

仅移除Desktop影音激活项，保留最新非影音配置；重新备份至`/Users/hrygo/.dsh/backups/media-separation-final-20261018T003504Z`。最终media与通用配置副本的实际工具验收通过，其他profile组合检查通过，FFmpeg合成片通过，备份哈希与回退保护夹具通过。后续非影音并行编辑继续保留，恢复脚本按设计拒绝覆盖。详见ACCEPTANCE.md。

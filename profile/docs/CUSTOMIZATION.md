# 本机 DSH 影音工作台深度定制方案

核验日期：2026-10-18。适用版本：本机已安装 DSH 0.2.1-rc.2；非上游功能承诺。验收原始收据见 `../checks/`，汇总结论见 ACCEPTANCE.md。

## 目标与范围

`media` 是独立 Web profile，集中 ComfyUI、SpeechRail、ImageHive 与 FFmpeg 的任务入口，通用 profile 不注册影音专用工具。复用现有推理服务、权重和素材目录，保留现有 Desktop 的编码/数据库/记忆能力，不修改 DSH 核心。

工具注册、上下文与依赖在 profile 层分开；GPU、统一内存、模型服务、文件与队列仍共享。profile 不是安全沙箱，也不能单独限制其他客户端占用资源。

## 组成与职责

| 组件 | 职责 | 接入方式 |
|---|---|---|
| ComfyUI | 工作流图像、编辑、视频、音乐 | 已安装官方 comfy-mcp，stdio，明确 COMFY_BIN |
| SpeechRail | ASR、配音、分离与音色操作 | 复用既有 speechrail-mcp 入口，首次 describe |
| ImageHive | 独立图像生成/编辑/VQA | 复用既有 DSH 协议 adapter 与 daemon |
| FFmpeg / FFprobe | 媒体规格、抽帧、转码、字幕、混音与合成 | media preset 的 bash 工具，原生 CLI |
| PTC Tool Search 0.1.1 | 按需载入调用声明 | 从现有已安装制品打包，独立固定 tarball 和 lockfile |
| media preset | 创作角色、精简工具、操作约束 | 本 profile 的 preset-media，默认选择 media |
| media-workbench / speechrail | 阶段操作说明 | 专用 skills 目录，不扫描全部个人技能 |

`media` 不安装 codebase-memory、personal-kb 或 LSP 工具。Hindsight 由既有 home patch 继承，保持原有路由。对话模型配置复制本次 Desktop 的既有 provider/default-model 行，不默认修改供应商、密钥或模型；以后两个 profile 的模型配置独立维护，不自动同步。

## 工具分离与配置所有权

- Desktop 移除 SpeechRail、ImageHive 两条 MCP 配置，以及 image-gen 行和 dsh-image-gen bundle 激活项。保留已安装依赖制品，便于原样回退；其余社区插件不清理。
- headless / sdk / web 现有 patch 不改；全局 home patch 不加影音工具。media 的三个 MCP 位于 media profile 层。
- 原 dsh-image-gen 是另一条生图链，本次从通用配置停用；media 只启用用户要求的 ComfyUI 与 ImageHive 图像能力，原生图配置保留在备份中。
- 全局已有 SpeechRail 技能链接属于操作知识，不是工具注册，本次保留；media 的技能发现只扫描专用目录。
- preset-media 基于本机实际安装版本的 ptc 模板裁剪：保留文件、shell、jobs、技能、压缩、交互与交付；去掉编码委派、网页搜索、计划/目标/日程及插件管理工具。其他自带 preset 保留供显式切换，默认新会话走 media。
- profile patch 是持久配置；会话只读工具列表必须实测。既有会话可能保留旧 composition，迁移后应新建会话核验，不强制打断现有任务。

## 上下文优化

PTC Tool Search 按 agent 建立检索目录，只把已选工具逐步加入 SDK；先检索、结束当前 run_code，再于下一请求调用。三个 MCP 仍在 profile 启动时连接，工具搜索不减少启动连接数，也不是延迟启动服务。

角色说明固定为短规则，复杂流程放在按需技能；当前阶段只读需要的模型/工作流信息，不输出全量节点目录、语音库存、完整工作流或 base64 媒体。每个独立项目使用新会话，避免已发现工具随长期会话持续累积。

本次不套用原插件其他场景的 token 百分比。用实际初始工具声明、注册集合与技能目录验证机制；后续若评估成本，分别统计总 input、uncached input、缓存命中、工具往返和实际账单。

## 运行与资源策略

Web 仅监听 127.0.0.1:3088，避免默认 3080 与现有 Desktop 随机端口混淆；端口占用时应明确失败，不自动终止占用者。通过 `dsh --profile media --no-open` 启动，无新增 LaunchAgent 或系统服务。ComfyUI 仍由 Comfy Desktop 持有。

操作策略为一路重推理：ComfyUI / ImageHive / SpeechRail 重模型任务串行，文件分析与轻量检查可穿插。每次重渲染前查询共享队列；排队任务不代表可直接取消。此处是技能与角色规则，不是跨服务强制调度器；如日后要自动准入，应独立设计共享锁与所有客户端接入，而非假称已限制 GPU。

ComfyUI 验证、提交和取回分开：validate → run_workflow(wait=false) → 立即落 prompt_id → status 短查 → fetch_outputs。传输超时与任务终态分开，重连优先按原 ID 查询，不自动重投或清队列。DSH jobs-local 记录随进程退出消失，不承诺任务恢复；ComfyUI 自身也可能重启丢失历史。

MCP 控制调用使用有界超时；SpeechRail / ImageHive 沿用已有 300000ms，ComfyUI 为 60000ms。超时只结束等待，不承诺远端工作已取消。取消前核对服务、ID、所属项目与当前状态。

## 工作流与品质定制

工作流权威入口：`/Users/hrygo/ComfyUI-Shared/workflows/active/`；模型及 MPS 参数 SSOT：`/Users/hrygo/ComfyUI-Installs/agent-tools-setup/MODELS.md`。每个项目复制母版后改输入，不改发布母版。flat 与 UUID subgraph 按创作目录 AGENTS.md 选择编辑方法。

正式图像原生 2048²；低清仅用于明确的小样，不后置放大冒充。H3 保留当前 TE CPU、视频 VAE FP16 等已验证设置；量化文件大小不代表 MPS 原生量化加速。当前视频/音乐验收限度沿用领域 SSOT，模型版本升级后重新出片，不从本次服务连通性外推品质。

FFmpeg 是系统 CLI；通用 profile 的 shell 仍可显式调用它，本次不卸载可执行文件，也不将 profile 当命令权限限制。FFmpeg 执行前先 ffprobe，使用新文件和 -n，显式映射音视频；先核对素材规格再决定是否重编码。可兼容交付 MP4 使用 H.264/AAC、yuv420p、faststart，但不强迫所有素材重编码。字幕单独保留 UTF-8 SRT/ASS，并核查中文字体。

技术验收与审美验收分列：解码、尺寸、时长、帧率、音轨、静音尾和响度是技术项；听感、歌词、音乐性、口型、全帧稳定与身份一致性仍需要对应检查或人工确认。只有当前路由已证明支持 image 输入时，MCP 图片才可进入模型上下文。本次继承的模型列表声明为 text，未修改能力声明、未验证视觉请求，不能承诺模型看图复核。音视频以文件交付，不能假称模型已听过声音。

## 项目与数据

默认项目位于 `/Users/hrygo/ComfyUI-Shared/projects/<唯一项目名>/`，使用 input / workflows / output / previews 和 project.json。清单记录输入、目标规格、seed、工作流哈希、模型/工具版本、任务 ID、产物及验收状态，不保存凭据。

present 只声明现有文件，不复制或永久托管；移动/删除源文件会使历史交付失效。成片与源素材保留在项目内，不写到临时目录当作长期交付。批量成品交付另列索引。

本地工具不等于全离线：沿用的对话 provider 可能在远端。敏感项目在发送素材或图像前确认模型路由和上下文传播范围，不将“未使用云渲染”写成“素材从不离机”。

## 可观测与验收

本次验收包括最终组合、实际 profile 启动、媒体 preset 工具发现、三个 MCP 只读调用、专用技能目录、FFmpeg 一秒合成片和 FFprobe 核验，以及分离后通用工具集合。默认不生成新的模型媒体，避免干扰已有共享队列；如需质量验收，另建明确项目并记录成本。

SpeechRail describe 当前 jobs.spool_ready=false、runner_active=false，ASR/TTS readiness=true。同步能力与持久 jobs 分开；本次不扩大到 SpeechRail 服务部署修复。对话模型真实请求、长任务断线恢复与完整成片品质不由只读验收证明，报告单列实测与未测。

## 后续优化顺序

1. 先用真实图像/配音/短视频项目采集人工操作耗时、失败原因和结果规格；每次只优化出现的瓶颈。
2. 若长配音/转写成为常用需求，再单独完善 SpeechRail 持久 runner，执行重启和结果取回验收。
3. 重复合成需求出现后再参数化字幕、混音、封面和批量导出模板，优先复用 FFmpeg 原生命令。
4. 跨服务同时使用频繁时再设计统一资源调度；需要 DSH 内置音视频播放器时作为独立 UI 功能评估。

回退入口与具体备份目录由 README.md / ACCEPTANCE.md 提供；恢复脚本只在当前文件哈希与本次修改后记录一致时覆盖通用配置，出现并行改动即停止。

---
name: media-workbench
description: 本机 media profile 的图像、视频、配音、转写、音乐与 FFmpeg 合成工作流；用于影音创作、素材检查和交付。
---

# 本机影音工作台

## 开始与路由

1. 明确目标类型、尺寸、时长、帧率、语言、字幕和交付格式；未指定时先提出与素材匹配的规格，不擅自降画质。
2. ComfyUI 生成、编辑及视频优先复用 `/Users/hrygo/ComfyUI-Shared/workflows/active/`。先读 `/Users/hrygo/ComfyUI-Shared/AGENTS.md` 与 `/Users/hrygo/ComfyUI-Installs/agent-tools-setup/MODELS.md` 的相关部分。
3. 所有 ComfyUI 服务调用走 `mcp__comfyui__*`。首次 `server_info`、`system_stats` 核对服务器和真实输入/输出目录；不使用历史 `workspace.path` 创建工程，不另起 server。
4. SpeechRail 配音与转写先加载 `speechrail` 技能，再调用 `describe`。使用当前参数、可用系统音色和 readiness；不自动切 profile。持久 runner 不就绪时只用同步能力并说明限制。
5. ImageHive 是独立生图/编辑服务。仅明确指定、需要其已验证能力或 ComfyUI 路线不适配时选择；先 model_status，不为切工具自动卸载另一个服务。
6. FFmpeg/FFprobe 使用 shell 的原生 CLI；不引入额外媒体 MCP。先通过 tool_search 查找 bash，结束该 run_code，下一次再执行发现的工具。

## 渲染与资源

- 先查共享队列，保留其他客户端任务。只提交当前任务的工作，默认一路重推理；将 ComfyUI、ImageHive、SpeechRail 的重模型调用串行。此为操作策略，不能强制控制其他客户端。
- 原生 2048² 图像沿用本机已验路线；视频先小样再正式只在用户认可预览规格时采用。H3 的 TE CPU、视频 VAE FP16 等兼容条件以 SSOT 为准，不用量化文件名推断计算速度。
- 从 active 复制到独立项目目录后改参数；flat 用可用 slots，UUID subgraph 按现有手册同步位置、命名值和 link，随后 live validate。验证通过仍须实际出片验收。
- run_workflow(wait=false)，立即记录 prompt_id、工作流路径和参数；短查 job status，完成后 fetch_outputs。断线、超时先按原 ID 查状态，不重复提交。取消只针对已核实属于本任务的 ID，不清空队列。
- 不自动安装节点、下载/删除权重、启动云节点、上传素材、重启服务或修改内存策略。若必须扩大这些范围，先说明影响和回退。

## FFmpeg 与质量检查

- 每个任务创建独立目录，输入只读；执行前 ffprobe 输出 JSON，检查真实宽高、帧率、时长、音轨和字幕。生成新文件用 ffmpeg -n，显式 -map，不默认覆盖。
- 最终 MP4 兼容交付可在用户没有特殊要求时采用 H.264 + AAC、yuv420p、+faststart；分辨率、帧率、码率与原素材/目标协商，不把此建议当固定强制转码。
- 合成只在需要时转码；可无损复用时评估 stream copy。字幕分开保存 UTF-8 SRT/ASS，烧录时检查本机字体和中文显示。
- 检查容器、解码、预期时长与音视频轨；视频抽首中尾帧。音频检查静音尾、峰值和响度，但机器指标不代替人工听感、口型、音乐性和身份一致性验收。
- 文件输出与技术指标通过不代表所有画面或音频质量通过；在交付记录中分别列出已检与待人工项。

## 目录与交付

默认任务目录 `/Users/hrygo/ComfyUI-Shared/projects/<唯一项目名>/`：`input/`、`workflows/`、`output/`、`previews/`，及 `project.json`。执行前确保项目名未占用，文件写入拒绝覆盖。
`project.json` 至少记录目标规格、素材路径、工具/工作流版本或哈希、seed/主要参数、prompt_id/语音 job_id（如有）、输出路径、验收状态；不保存凭据。长任务每次提交后立即更新。
最终用 present 声明成品与清单。present 保存路径声明，不复制媒体；保留源文件位置。图像可预览，音频视频通过实际文件打开，不声称 MCP 已把声音传给模型。

## 上下文与隐私

只加载当前阶段工具及技能；不要把节点完整列表、全量工作流或 base64 媒体反复打印给模型。工具搜索的选择在会话内累积，换任务可新建会话。
推理工具在本机不等于 LLM 对话离线；当前对话模型路由继承 Desktop。对敏感素材，先确认选用本地模型且不会将画面/文本传给远端。

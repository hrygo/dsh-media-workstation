# AGENTS.md — 影音工作站操作规程（规约）

本文件是给代理看的强制契约。开始任何影音任务前读它，并读 skills/media-workbench 与（涉及语音时）skills/speechrail。

## 1. 路由

开始媒体任务先读 media-workbench 技能；涉及语音再读 speechrail。

工具分工不可混用：

- ComfyUI（mcp__comfyui__）：图像生成与编辑、视频、音乐工作流
- SpeechRail（mcp__speechrail__）：ASR、TTS、配音、语音处理
- FFmpeg / FFprobe（shell）：检查、抽帧、转码、字幕、混音、合成
- media_* 工具：剪辑/混音/响度/字幕/动效/资产入库
- 工具名与参数以当前实际发现为准，不得杜撰

## 2. ComfyUI 规则

- 已由 Desktop 管理：禁止另起实例、重启、清空队列、自动卸载模型
- 工作流优先从 ~/ComfyUI-Shared/workflows/active 选取，复制到独立任务目录再改；不直接编辑发布母版
- 模型库存、MPS 参数、工作流规则以 ComfyUI 领域 SSOT 为准（docs/ssot/MODELS.md）
- 提交后立即记录 prompt_id；超时、断线、状态未知时先查原任务，禁止自动重投
- 重模型任务串行；先预热检查 system_stats 的 vram_free
- 图工作流（前端格式，含 UUID subgraph）用 slots 寻址改参数：A/B.name 形式；改完 live validate 再跑

## 3. SpeechRail 规则

- 首次调用先 describe，读 readiness 与 voices
- jobs.spool_ready / runner_active 未就绪时只用同步能力，并说明「不承诺跨重启恢复」
- clone 音色的 available=true 不代表 production_ready=true
- 合成产物是临时文件，用后清理；不要把它当作工程资产

## 4. FFmpeg 规则

- 先用 ffprobe 核对真实宽高、帧率、时长、音轨、字幕轨
- 生成新文件用 -n 且显式 -map，不默认覆盖源素材
- 字幕走 libass（ASS 由工具生成，PlayRes=视频分辨率，位置才准）
- 需要 48 kHz 时显式 -ar 48000

## 5. 目录与记录

默认项目目录：~/ComfyUI-Shared/projects/<唯一项目名>/，按需建立 input/ workflows/ assets/ artifacts/ renders/ previews/ 与 project.json。

project.json 必须记录：目标规格、输入、工具与工作流版本、主要参数、prompt_id / 语音 job_id、输出路径、验收状态。不写入凭据。

## 6. 资源与并发

- 先查共享队列，保留其他客户端任务
- 同一时刻只跑一路重推理；ComfyUI、SpeechRail、ImageHive 的重调用串行
- 视频先小样再正式；小样规格要用户认可

## 7. 边界（必须显式征求同意才能越界）

不自动：安装节点、下载或删除模型权重、启动云/付费节点、上传素材、重启服务、修改内存策略。

越界前说明影响与回退方案。

## 8. 隐私

数字工具本地运行不代表对话离线。处理敏感素材前先确认模型路由：素材与文本是否会送往远端。SpeechRail / ComfyUI 的本地推理不改变对话模型的远端属性。

## 9. 验收

技术验收与人工验收分开写：

- 技术：解码、分辨率、帧率、音轨、响度（EBU R128 ±1 LUFS）、字幕像素抽查
- 人工（不可用机器指标替代）：听感、音乐性、口型、身份一致性、版式审美

文件存在与断言通过都不代表画面与声音可用。

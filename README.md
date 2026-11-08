# DSH Media Workstation

一个可直接复用的「本机影音创作工作站」完整工程：DSH media profile 的插件与桥接代码、Skills、SOP、规约文档，加上经过实测验证的 ComfyUI 工作流清单与缺陷修复补丁。

目标不是再做一个 MCP 服务器，而是把「本机 ComfyUI 出图/出片 + SpeechRail 配音转写 + FFmpeg/Remotion 剪成片」这套流程固化成**可安装、可验证、可回滚**的一组文件。

## 已验证状态

硬件基线：Apple M5 Max / 128 GiB 统一内存 / macOS（17 万权重 165.84 GiB 在本机，不入库）

| 面 | 状态 | 证据 |
|---|---|---|
| 媒体工具链（om 桥 / ffmpeg / Remotion） | 通过 | media_doctor 全绿；ffmpeg 9.0.2、node v26.12.1 |
| 剪辑 / 混音 / 响度 / 换轨 | 通过 | 全链路成片 1280x720@30 + aac 48k + -14.0 LUFS，probe 断言全过 |
| 字幕（libass 中文） | 通过 | 底部与顶部位置均抽帧确认 |
| Remotion 动效 | 通过 | HeroTitle / EndTag / TitledVideo(含 props) |
| SpeechRail TTS / ASR | 通过 | quality/quality；同步 synthesize + transcribe（含时间戳、说话人） |
| ComfyUI 工作流（9 份） | 通过（live validate 9/9） | comfy-cli 1.22.0，ComfyUI 0.44.2，MPS，8188 |
| 2K 图像出图 | 通过 | img_default_2k → 2048x2048 rgba PNG，约 20 分钟（含权重冷加载），prompt_id 见 docs/07-verification.md |
| 图像 provider（openai-compat） | 通过 | gpt-image-2.5-flare 出图（尺寸需后续对齐） |

未纳入自动验证的部分（必须人工确认）：听感与音乐性、配音自然度、版式审美、口型一致性。技术指标通过不等于这些通过。

## 仓库结构

    dsh-media-workstation/
      AGENTS.md                 代理操作规程（规约）：工具分工、边界、验收
      profile/                  DSH media profile 的可安装副本
        bin/om, bin/om_cli.py   媒体桥接 CLI（含本仓修复）
        cordis.yml              根（空）
        cordis.patch.yml        bundle + MCP 客户端注册（comfyui / speechrail / imagehive）
        package.json            profile bundles
        skills/                 media-workbench、video-pipeline
        docs/                   profile 自带文档
      docs/
        01-architecture.md      组件与数据流
        02-tool-surface.md      media_* 工具与 om 子命令速查
        03-sop-edit-pipeline.md 剪片 SOP
        04-sop-generation.md    ComfyUI 生成 SOP
        05-sop-voice.md         SpeechRail SOP
        06-conventions.md       目录、资源、隐私、边界
        07-verification.md      三轮自检 + ComfyUI live 验证记录
        08-defects-and-fixes.md 缺陷清单与修复补丁说明
        ssot/                   本机 SSOT：ComfyUI-Shared AGENTS、MODELS 清单
      workflows/active/         9 份可直接导入的执行工作流（图工作流，含 subgraph）
      patches/                  对 OpenMontage 与 om 桥的修复 diff
      examples/                 edit_decisions / SRT / project.json / schema
      scripts/                  install.sh、verify.sh

## 架构

    DSH (media profile)
      ├── cordis bundles ── MCP 客户端
      │     ├── comfyui      → comfy-cli → ComfyUI Desktop 127.0.0.1:8188 (MPS)
      │     ├── speechrail   → SpeechRail 127.0.0.1:8201/v1
      │     └── imagehive    → imagehived（可选，独立生图）
      └── media workstation 工具 (media_*) ── shell ── om CLI
                                                        ├── OpenMontage (compose / schema / pipelines)
                                                        ├── ffmpeg 9.x（剪辑、混音、响度、字幕、抽帧）
                                                        └── Remotion（动效、图文成片）

数据只落在两处：生成物在 ComfyUI 输出目录，工程与成片在本仓约定的 projects 目录。

## 快速开始

1. 安装 profile（会先备份现有目录）：

    ./scripts/install.sh            # 备份 + 软链或复制到 ~/.dsh/profiles/media

2. 自检：

    ./scripts/verify.sh             # 等价于 om doctor + 冒烟成片 + 断言

3. 依赖（本机需已具备，本仓不安装）：

- ffmpeg / ffprobe 9.x（含 libass、loudnorm、ebur128、sidechaincompress）
- node + Remotion（OpenMontage/remotion-composer）
- OpenMontage 仓库（om 桥通过 OPENMONTAGE_HOME 指向它）
- ComfyUI Desktop（由 App 管理，本仓不启停、不清队列）
- SpeechRail（本地服务，可选）

## 路径约定

profile 配置里的绝对路径按本机写死（comfy-mcp、speechrail-mcp、ImageHive 等）。换机器时改 profile/cordis.patch.yml 里的 command 与 env 即可，其余文件不含机器专属路径（examples 用 $PROJECT 占位）。

## 这个仓做对了什么（相对原始预设）

详见 docs/08-defects-and-fixes.md：

- edit_decisions 现在真的按 JSON Schema 校验，自创/拼错字段与非法枚举会被拦下
- 旁白超长会告警，不再静默截断音尾
- norm 按输出容器选编码器，.wav 不再产出坏文件
- subtitles.style 字符串不再让整条片子渲染崩溃；position 生效
- 换轨统一 48 kHz
- Remotion 支持 --public-dir，素材不用再塞进共享 public

## License

MIT

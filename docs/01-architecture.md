# 01 架构

## 分层

    ┌──────────────────────────────────────────────────────────────┐
    │ DSH media profile                                            │
    │  cordis.yml（空根）+ cordis.patch.yml（bundle 与 MCP 注册）   │
    │  bundles: dsh-base, dsh-web-app, dsh-ptc-tool-search         │
    ├──────────────────────────────────────────────────────────────┤
    │ MCP 客户端                      │ media workstation 工具      │
    │  comfyui  → comfy-mcp           │  media_doctor / guide       │
    │  speechrail → speechrail-mcp    │  media_collect / compose    │
    │  imagehive → imagehived（可选） │  media_audio / motion       │
    │                                 │  media_probe                │
    └───────────────┬─────────────────┴──────────────┬──────────────┘
                    │                                │ shell
        ┌───────────▼──────────┐          ┌──────────▼───────────┐
        │ ComfyUI Desktop      │          │ om 桥 (bin/om_cli.py) │
        │ 0.44.2 · MPS · :8188 │          │  compose / validate   │
        │ 输出 ~/ComfyUI-Shared│          │  mix / norm / attach  │
        └──────────────────────┘          │  probe / burn         │
                                          │  remotion             │
                                          └──────────┬───────────┘
                                                     │
                              ┌──────────────────────┼─────────────────────┐
                              │ OpenMontage          │ ffmpeg 9.x          │
                              │ （compose、schema、  │ （编码、滤镜、响度） │
                              │  pipelines、validator）│                    │
                              │ remotion-composer    │                     │
                              └──────────────────────┴─────────────────────┘

## 为什么桥接而不是直连

- 剪辑、混音、响度、字幕这套动作需要可断言的命令行行为与退出码；把它们收进一个薄 CLI（om），既给人用也给工具用，工具与 CLI 参数同名，坏了可以直接退回 shell 复现。
- OpenMontage 是重资产（管线、schema、Remotion），不适合塞进 MCP 服务器；桥接只暴露剪辑/记账那一半。
- 生成永远走 ComfyUI MCP，语音永远走 SpeechRail MCP：两侧各自有队列、显存与生命周期语义，桥接不复制这些逻辑。

## 数据流（一次成片）

    ComfyUI 出片段 → media_collect 入库 assets/
                    → 写 artifacts/edit_decisions.json（先读 schema）
                    → media_compose（校验 + 渲画面）
    人声/配乐        → SpeechRail synthesize / 外部配乐
                    → media_audio mix（以画面为时长基准）
                    → media_audio norm（-14 LUFS，48 kHz）
                    → media_audio attach（换轨不重编码）
                    → media_probe（宽高/帧率/音轨/响度断言）

## 关键约定

- 画面与声音分两次落盘：先出无声画面，再 mix/norm，最后 attach。因为 compose 带 audio 参数时会按音频长度裁画面（已实测）。
- 所有工程产物在 ~/ComfyUI-Shared/projects/<项目>/；生成物留在 ComfyUI 输出目录，由 collect 挑进来。
- profile 里的 MCP 命令是本机绝对路径，换机需改 cordis.patch.yml。

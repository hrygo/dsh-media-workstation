# 02 工具面速查

## media_* 工具

| 工具 | 参数（关键） | 说明 |
|---|---|---|
| media_doctor | — | 自检 om 桥、ffmpeg 滤镜、Remotion、node、ComfyUI 端口 |
| media_guide | action=pipelines\|skills\|schema；pipeline | 管线清单、阶段指南、edit_decisions schema |
| media_collect | project, sinceHours?, limit? | 把 ComfyUI 输出搬进 <project>/assets，只复制不删除 |
| media_compose | composition, out, audio?, subtitles? | 先校验再渲染；subtitles 传 SRT 会 libass 烧录 |
| media_probe | input, expect[], loudness? | ffprobe 摘要 + 断言，必要时测 EBU R128 |
| media_audio | action=mix\|norm\|attach；voice/music 或 input 或 video/audio；out；musicGain?/lufs? | 侧链混音、响度归一、换轨 |
| media_motion | composition, out, props?, scale?, frames? | Remotion 渲染动效与图文成片 |

注意：media_compose 的决策文件参数名是 composition（不是 decisions）。参数名写错时工具会去/undefined 找文件，报错并不友好。

## om 子命令（与工具同名，可单独复现）

    om pipelines [--json]
    om skills <pipeline> [--show N]
    om validate <composition.json> [--runtime ffmpeg|remotion|hyperframes] [--assets-root DIR] [--json]
    om compose <composition.json> --out X.mp4 [--audio Y] [--subs Z.srt] [--profile P] [--codec libx264] [--crf 20] [--preset medium]
    om probe <media> [--loudness] [--expect key=value]... [--json]
    om burn <video> --srt X.srt --out Y.mp4 [--position top-center|center|bottom-center] [--size 46] [--margin 72]
    om mix --voice A --music B --out C [--music-gain 0.28] [--threshold 0.03] [--ratio 8] [--release 350]
    om norm <input> --out X [--lufs -14] [--tp -1.5] [--lra 11]
    om attach --video V --audio A --out O
    om remotion <composition> --out O [--props P.json] [--scale 0.35] [--frames 0-59] [--public-dir DIR]
    om doctor

## probe 断言键

width、height、fps、audio（yes/no）、codec、lufs（需 --loudness）。断言不通过时退出码非 0，可直接用于 CI 式校验。

## ComfyUI MCP 常用

server_info / system_stats / validate_workflow / list_workflow_slots / set_workflow_slot / run_workflow(wait=false) / job(status|wait|cancel) / fetch_outputs / search_models。

工作流是前端图格式（含 UUID subgraph）时，slots 地址形如 A/B.name；set_workflow_slot 传 stdout=false 才会写回文件。

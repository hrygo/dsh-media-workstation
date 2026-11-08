---
name: video-pipeline
description: 把多段素材做成一条成片：写 edit_decisions、校验、渲染、混音、响度归一、硬字幕与 ffprobe 断言。用 media_* 工具完成，成套镜头素材来自 ComfyUI。
metadata:
  short-description: 成片流水线（OpenMontage 契约 + 本机 ffmpeg/libass/Remotion）
---

# 成片流水线

单件素材用 ComfyUI 生成，语音用 SpeechRail，**把素材剪成一条片**走本流程。

## 工具

本预设挂载 `dsh-media-workstation`，优先用工具，不要先回落到 shell：

| 工具 | 用途 |
|---|---|
| `media_doctor` | 自检 om 桥、ffmpeg 滤镜、Remotion、ComfyUI 是否在线 |
| `media_guide` | `pipelines` / `skills` / `schema`（写 JSON 前先读 schema） |
| `media_collect` | 把 ComfyUI 新产物搬进 `<project>/assets` |
| `media_compose` | 校验 + 渲 cuts，可带字幕 |
| `media_probe` | ffprobe 断言，`loudness` 测 EBU R128 |
| `media_audio` | `mix` / `norm` / `attach` |
| `media_motion` | Remotion 动效与图文成片 |

工具不可用时退回 `$HOME/.dsh/profiles/media/bin/om`，参数与工具同名。

## 项目布局

```
~/ComfyUI-Shared/projects/<项目名>/
  assets/        生成片段、实拍、配乐
  artifacts/     edit_decisions.json、subs.srt、混音件、collect 清单
  renders/       成片
  project.json   规格、seed、工作流、任务 ID、验收状态
```

## 出片顺序

1. **入库**：`media_collect` 把 ComfyUI 输出搬进 `assets/`，看清单确认文件名与体积。
2. **写时间轴**：先 `media_guide action: schema` 读 `edit_decisions` 的 schema，再落盘。
3. **校验+渲染**：`media_compose`（默认先校验）。只出画面，此时**不要**传短音频。
4. **混音**：`media_audio action: mix`，`voice` 指向刚渲出的片子（时长基准即画面），`music` 是配乐。
5. **响度**：`media_audio action: norm` 到 `-14 LUFS`，再 `attach` 回画面。
6. **字幕**：`media_compose` 的 `subtitles`，或单独烧录。
7. **断言**：`media_probe` 带 `expect`（宽高/帧率/音轨/`lufs=-14`），全过再 present。

## edit_decisions 最小形状

```json
{
  "version": "1.0",
  "render_runtime": "ffmpeg",
  "composition_mode": "cuts",
  "renderer_family": "ffmpeg",
  "cuts": [
    {"id": "c1", "source": "/abs/assets/a.mp4", "in_seconds": 0.0, "out_seconds": 3.0},
    {"id": "c2", "source": "/abs/assets/b.mp4", "in_seconds": 1.2, "out_seconds": 4.5}
  ],
  "metadata": {"compose_target": {"width": 1920, "height": 1080, "fit": "pad"}}
}
```

`id/source/in_seconds/out_seconds` 必填，字段名不可自创。竖屏改 `1080x1920`；`fit` 用 `pad` 或 `cover`。

## 管道

| 管道 | 适用 |
|---|---|
| `documentary-montage` | 实拍/素材剪主题片 |
| `animated-explainer` | 生成图/片段 + 旁白 + 字幕 |
| `clip-factory` | 长素材切多条短片 |

`media_guide action: skills` 看某个管道的阶段指南再动手。

## 四条硬约束

1. **音频长度决定成片长度**：`compose` 带 `audio` 会 `-shortest` 截断画面。声音永远在画面之后接。
2. **`mix` 以 `voice` 时长为准**：传画面文件，不传短音频。
3. **字幕走 libass**：工具内部生成匹配视频分辨率的 ASS；不要手写 `-vf subtitles=`。
4. **`norm` 会重采样**：工具已强制 48 kHz；自己拼 ffmpeg 时别漏 `-ar 48000`。

## 交付判据

- `media_probe` 断言全过；响度落在目标 ±1 LUFS。
- 字幕抽查开头与结尾各一帧，确认中文不是方块。
- 技术验收（解码/响度/帧率）与审美验收（听感/节奏/口型）分开写。
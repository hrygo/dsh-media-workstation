# 03 SOP：把素材剪成一条片

前置：读 AGENTS.md；确认 project 目录未被占用。

## 步骤

1. 入库
   media_collect(project=...)，看清单确认文件名与体积。只复制，不删除源。

2. 写时间轴
   先 media_guide action=schema 读 edit_decisions 的 schema，再落盘。字段名不可自创（现在会被 validate 拦下）。

   最小形状（ffmpeg 运行时）：

       {
         "version": "1.0",
         "render_runtime": "ffmpeg",
         "composition_mode": "cuts",
         "renderer_family": "ffmpeg",
         "cuts": [
           {"id": "c1", "source": "/abs/assets/a.mp4", "in_seconds": 0.0, "out_seconds": 3.0},
           {"id": "c2", "source": "/abs/assets/b.mp4", "in_seconds": 1.2, "out_seconds": 4.5, "transition_in": "fade", "transition_duration": 0.4}
         ],
         "metadata": {"compose_target": {"width": 1920, "height": 1080, "fit": "pad"}}
       }

3. 渲染画面（不要在这一步塞短音频）
   media_compose(composition=..., out=renders/base.mp4)

4. 混音
   media_audio(action="mix", voice=renders/base.mp4, music=music.wav, out=artifacts/mix.m4a)
   voice 指向**刚渲出的画面**，时长基准才是画面。

5. 响度
   media_audio(action="norm", input=artifacts/mix.m4a, out=artifacts/mix_norm.m4a, lufs=-14)
   输出扩展名决定编码器：.wav 得 PCM，.m4a 得 AAC；两者都已是 48 kHz。

6. 换轨
   media_audio(action="attach", video=renders/base.mp4, audio=artifacts/mix_norm.m4a, out=renders/final.mp4)

7. 字幕（可选）
   media_compose(..., subtitles=artifacts/subs.srt) 或 om burn --position top-center

8. 断言
   media_probe(input=renders/final.mp4, expect=["width=1920","height=1080","fps=30","audio=yes","lufs=-14"], loudness=true)

## 实测得到的四条硬约束

1. compose 传 audio 参数会按音频长度裁画面（6s 画面 + 4.8s 旁白 → 4.8s 成片）。声音永远在画面之后接。
2. edit_decisions.audio.narration 走的是另一条路径：音频被补长到画面长度，画面不裁，但超长旁白会被静默截断——validate 现在会给 warning。
3. 字幕位置：走 media_compose 的 subtitles 参数（om burn 路径，PlayRes=视频分辨率）才能像素级定位；写进 edit_decisions.subtitles.position 也能生效，但字号/边距在 libass 脚本空间，属粗定位。
4. norm 强制 48 kHz；compose --audio 换轨也已强制 48 kHz（本仓修复）。

## 交付判据

- probe 断言全过，响度落在目标 ±1 LUFS
- 字幕抽开头与结尾各一帧，确认中文不是方块
- 技术验收与人工验收分开写（听感、节奏、口型、音乐性机器指标替代不了）

# 05 SOP：SpeechRail 配音与转写

## 先 describe

任何语音调用前先 describe，读：

- profile（本机 quality/quality，consistent）
- readiness.asr / tts / diarization
- voices[]：id、name、mode（system / clone）、available、production_ready
- jobs：spool_ready / runner_state

本机现状：三个能力都就绪；jobs.spool_ready=false、runner_state=unconfigured，因此**只用同步能力**，不做跨重启恢复承诺。

## 合成（TTS）

    synthesize(text="...", voice="serena", output_format="wav", speed=1.0)

- voice 默认 serena（温柔中文女声）；本机系统音色：serena、vivian、uncle_fu、dylan、eric、aiden、ryan、ono_anna、sohee
- clone 音色需 available=true；available=true 不等于 production_ready=true
- 输出是临时文件（/var/folders/...），要留就复制进项目 assets/
- 返回 wav 为 24 kHz 单声道；交付前要 48 kHz 请显式重采样（mix/norm 会处理，单独用则自己加 -ar 48000）
- 长文本按 4096 字符切段，分段合成后再拼接；分段要按句子边界切，避免断气

## 转写（ASR）

    transcribe(audio_ref="/abs/file.wav", language="zh")
    transcribe(..., timestamps=true)   # 逐字/逐段的时间戳
    transcribe(..., diarize=true)      # 说话人分离，需 diarization_ready

本机实测：4.8s 中文旁白 → 文本逐字一致；timestamps 给到 0.16s 粒度；diarize 输出 speaker A 单段。

## 口型/数字人

avatar 类任务用 head-avatar 技能；SpeechRail 只负责音频渲染，不做口型对齐。口型一致性属于人工验收项。

## 与剪辑衔接

1. TTS 出旁白 → 复制进 assets/narration.wav
2. 需要 48 kHz：ffmpeg -i narration.wav -ar 48000 -ac 1 narration48.wav
3. 若走 edit_decisions.audio.narration：validate 会检查旁白是否超出画面（超了给 warning，因为会被静默截断）
4. 若走 mix：voice 传**画面文件**，音乐做侧链；再 norm -14 LUFS；再 attach

## 纪律

- 音色不是真人模仿，指令要描述声学特征（性别/年龄/音高/语速/情绪），不要指向真实人物
- 不做「发布即生产就绪」的假设：candidate 通过机器校验不等于人耳通过
- 语音产物与视频产物分开验收：文本正确性、断句、情绪、口型

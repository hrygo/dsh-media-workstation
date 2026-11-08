# 07 验证记录

三轮自检 + 一次 ComfyUI live 验证。所有数字来自本机实测，不是文档抄录。

## 硬件与版本

| 项 | 值 |
|---|---|
| 机器 | Apple M5 Max / 128 GiB 统一内存 / macOS（Darwin 27） |
| ffmpeg / ffprobe | 9.0.2 |
| node | v26.12.1 |
| comfy-cli | 1.22.0 |
| ComfyUI | 0.44.2（Desktop standalone，MPS，127.0.0.1:8188） |
| SpeechRail | quality/quality，asr+tts+diarization ready |
| OpenMontage | 本机 checkout，remotion-composer 已装 |

## 第一轮：主链路

| 检查 | 结果 |
|---|---|
| media_doctor | 全绿（repo/venv/ffmpeg/ffprobe/pipelines/schemas/remotion/node/6 组滤镜） |
| edit_decisions schema | 可读（13,690 B） |
| compose 2 cuts | 6.021s / 1280x720 / 30fps / h264 yuv420p / aac 48k |
| 字幕硬烧（libass 46px） | 中文正常，非方块 |
| probe 正断言 | width/height/fps/audio 全过 |
| mix 侧链 | 成功（增益 0.28） |
| norm | -21.69 → -14.0 LUFS |
| attach | 成功（需 .m4a，见缺陷 3） |
| 成片断言 | 含 lufs=-14 全过 |
| media_motion HeroTitle / EndTag | 成功 |
| SpeechRail TTS | serena 中文 4.8s，production_ready |
| SpeechRail ASR | 文本逐字一致 |

## 第二轮：边界与失败路径

| 检查 | 结果 |
|---|---|
| media_collect | 扫描 ComfyUI 输出 35 个候选，复制 5 个入 assets |
| 竖屏 1080x1920 fit=cover | 通过 |
| 缺失素材 | 正确拒绝，报错明确，未产文件 |
| probe 负断言 | 正确失败（exit 1，期望 1920 实际 1280） |
| Remotion TitledVideo + props | 通过（中文 tagline 正常） |
| subtitles.font_size / position | 前者曾误判生效，后者不生效（缺陷 5） |
| TTS mp3 + speed 1.4 | 通过 |
| ASR timestamps | 逐字，0.16s 粒度 |
| ASR diarize | speaker A，4.8s |
| 图像 provider（openai-compat） | gpt-image-2.5-flare 出图 1254x1254（请求 1024²，尺寸漂移） |

## 第三轮：修复后回归

8 条缺陷的定位与修复见 08-defects-and-fixes.md，逐项验证结果：

| 验证 | 结果 |
|---|---|
| 合法 compose 文件 | PASS（仅无音频 warning，无误杀） |
| 拼错字段 transition / transitionin | FAIL：Additional properties are not allowed |
| 非法枚举 render_runtime="magic" | FAIL：not one of [...] |
| 8s 旁白 + 3s 画面 | warning：旁白超出画面，音尾会被截断 |
| norm → .wav | pcm_s16le / 48000 / wav，attach 成功 |
| style="sentence" | 渲染成功（此前崩溃） |
| style 为对象 | validate PASS |
| om burn --position top-center | 抽帧确认字幕在顶部 |
| compose --audio 采样率 | 24000 → 48000 Hz |
| om remotion --public-dir | 渲染成功，未污染共享 public |
| 既有工程 om-smoke-20261108 | validate 仍 PASS |
| 全链路回归 | 6.021s / 720p30 / 1 音轨 / -14.0 LUFS 全断言通过 |
| 本仓 scripts/verify.sh | 在全新目录跑通（compose→mix→norm→attach→probe 全过） |

## ComfyUI live 验证（服务启动后）

服务：server_info running=true，url=http://127.0.0.1:8188；system_stats：ComfyUI 0.44.2、PyTorch 2.12.1、Python 3.13.12、mps vram_total 137438953472 / vram_free 82527207424。

工作流静态+动态校验（validate_workflow，UI 图 → API 自动转换，含 UUID subgraph）：

| 工作流 | valid | warnings |
|---|---|---|
| img_default_2k | 是 | 0 |
| img_detail_2k | 是 | 0 |
| img_edit_default_2k | 是 | 1 |
| img_edit_fallback_2k | 是 | 1 |
| h3_t2v_default | 是 | 0 |
| h3_t2v_fallback | 是 | 0 |
| h3_t2v_preview | 是 | 0 |
| aud_mm_music3_default | 是 | 0 |
| aud_ace15xl_draft | 是 | 0 |

出图冒烟（已完成）：img_default_2k，set_workflow_slot 改 459.prompt 后 run_workflow(wait=false) 提交，prompt_id = d37a2b76-bfff-4e63-9af9-bece79accf1d。

| 项 | 结果 |
|---|---|
| 状态 | completed，error = null |
| 输出 | qwen_base_2k_00001.png（output/image/current 子目录） |
| 尺寸 / 像素格式 | 2048 x 2048 / rgba |
| 体积 | 3.7 MB |
| 端到端耗时 | 约 20 分钟（首次运行含权重冷加载，热跑显著更快） |
| 取件 | fetch_outputs(prompt_id, out_dir=...) 自动按 URL 拉取并落盘 |

画面与 prompt 一致（灰色影棚背景、方台 + 哑光球体、底部色卡条），说明 TE + int8 DiT + VAE 链路正常。

注意：生成物可能落在 output/image/current 这类子目录，不在 output 根目录；直接用 fetch_outputs 取，不要靠 ls 猜。

## 未纳入自动验证

听感、音乐性、配音自然度、口型一致性、版式审美。这些是人工项，机器指标通过不代表通过。

## 环境限制记录

- SpeechRail jobs.spool_ready=false、runner_state=unconfigured：只用同步能力，不承诺跨重启恢复
- ComfyUI 由 Desktop 管理：本仓不启停、不清队列、不卸载模型

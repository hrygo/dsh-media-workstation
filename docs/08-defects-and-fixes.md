# 08 缺陷与修复

验证过程中确认并修复的 8 条问题。逐条给出证据、改法与回滚。补丁在 patches/。

## 1. edit_decisions 完全没有 schema 校验（高）

证据：自创字段 zoomer、拼错的 transition / transitionin、非法枚举 render_runtime="magic"，全部通过 validate 并成功渲染。composition_validator 只做资产存在/时长/重叠的启发式检查，从不加载 schemas/artifacts/edit_decisions.schema.json。

影响：拼错一个可选字段，效果静默消失而不是报错。工具描述里「invented field 会在编码前失败」当时不成立。

改法：om validate 增加 _apply_schema_check()，用 jsonschema 按 schema 校验，violations 即 error 且 success=False。

验证：合法文件 PASS；transition / transitionin 报 Additional properties are not allowed；render_runtime="magic" 报 not one of [...]；既有工程 om-smoke-20261108 抽查仍 PASS（无误杀）。

## 2. 旁白超长静默截断（中）

证据：8s 旁白 + 3s 画面 → 输出 3.0s，无任何告警。validator 声称的 Narration duration exceeding video duration 检查在实现里不存在。

改法：_apply_narration_check()：按 cuts 与 speed 算画面时长，逐条比对旁白资产时长，超出即 warning。

验证：用例现在输出「旁白超出画面: music_bed.wav 到 8.00s，画面只有 3.00s，音尾会被截断」。

## 3. norm 无视扩展名固定 aac（中）

证据：media_audio norm 输出 mix_norm.wav → format_name=wav 但 codec_name=aac；随后 attach 解码报 decode_band_types: Input buffer exhausted，产出 261B 空文件。

改法：新增 _audio_codec_args()，按扩展名选编码器（wav/aiff/caf→pcm_s16le，mp3→libmp3lame，flac→flac，其余→aac），统一 48 kHz。

验证：norm → .wav 得 pcm_s16le / 48000 / wav，attach 成功，probe 全过。

## 4. subtitles.style 是字符串时整条渲染崩溃（高）

证据：schema 把 subtitles.style 定义为字符串（sentence/word-by-word），实现里按 dict 调 .items()，于是 schema 合法输入直接 fail：'str' object has no attribute 'items'。

改法：_resolve_subtitle_style 同时接受 str/dict；并把 schema 级字段 font / font_size / color / outline_color / background / position 映射进样式。schema 侧把 style 放宽为 string 或 object。

验证：style="sentence" 可渲染；style 为对象仍 PASS。

## 5. subtitles.position 被忽略（低）

证据：position="top-center" 时字幕仍在底部。

改法：om burn 增加 --position（ASS Alignment 8/5/2），cmd_compose 读 edit_decisions 的 position 与 font_size；video_compose 侧把 position 映射到 ASS alignment。

验证：om burn --position top-center 抽帧确认在顶部。compose 内联路径能离开底部但仍是粗定位（字号/边距在 libass 脚本空间），像素级定位请用 media_compose 的 subtitles 参数。

## 6. 两种音频接入路径采样率不一致（低）

证据：compose --audio 换轨保留源 24 kHz；edit_decisions.audio.narration 路径输出 48 kHz。

改法：两处 mux 路径统一 -ar 48000 -b:a 192k。

验证：换轨后 48000 Hz。

## 7. Remotion 不能引用绝对路径素材（中）

证据：TitledVideo 的 videoSrc 传绝对路径 → Remotion 拒绝 file://；om remotion 也没有 --public-dir，只能把素材塞进 ~/OpenMontage/remotion-composer/public。

改法：om remotion 增加 --public-dir（校验目录存在）。

验证：--public-dir 指向项目目录即可渲染，未污染共享 public。

## 8. schema 枚举与实际运行时冲突（中）

证据：文档给的最小形状用 composition_mode="cuts" 与 renderer_family="ffmpeg"，但 schema 枚举里都没有 → 一旦开了 schema 校验，合法文件会被误杀。

改法：schema 的 composition_mode 增加 cuts，renderer_family 增加 ffmpeg。

验证：examples/edit_decisions.json 通过校验。

## 文档与实测不符（未改代码，已记录）

| 文档说法 | 实测 |
|---|---|
| compose 带 audio 会 -shortest 截断画面 | 对 audio 参数成立（6s 画面 + 4.8s 旁白 → 4.8s）；对 edit_decisions.audio.narration 不成立（音频被补到画面长度，输出 6.02s） |
| 工具已强制 48 kHz | 仅 norm 成立；compose --audio 原本保留源采样率（已修） |
| 字幕 position 可自定义 | 桥接烧录路径可；compose 内联路径原本完全忽略（已修，粗定位） |

## 回滚

    # om 桥
    cp <backup>/om_cli.py ~/.dsh/profiles/media/bin/om_cli.py

    # OpenMontage
    cd ~/OpenMontage && git checkout -- tools/video/video_compose.py schemas/artifacts/edit_decisions.schema.json

补丁文件：

- patches/om-cli-media-fixes.diff（257 行）
- patches/openmontage-media-fixes.diff（96 行）

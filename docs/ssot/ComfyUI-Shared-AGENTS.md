# AGENTS.md — ComfyUI-Shared 创作项目

本目录所有创作任务（图生视频、文生视频、图像、音频）的执行手册，开工前必读。

## 1. 这是什么目录

- 路径 `/Users/hrygo/ComfyUI-Shared`，是 **Comfy Desktop 的共享存储目录**，不是 comfy-cli 的 project/1 工程。
- 无 `comfy.yaml` / `assets/` / `blueprints/` / `.comfy/`。不要调 `project` 相关工具（必报 `project_not_found`），不要 `project init`。
- Server 由 Desktop 独立启动（`deploy_environment: local-desktop2-standalone`），不是 `comfy launch` 起的：`get_logs` 永远 `no_log_file`——不要调，排障靠 `job(action="status"/"error")`。
- 目录约定：`input/` 源素材 · `models/` 本地模型（§5）· `output/` 直出（`audio/`、`video/`、`image/`）· `workflows/` 可复用工作流（§9）。
- 社交平台发布工具与账号状态的项目级 SSOT：根目录 [发布工具.md](发布工具.md)；作品目录投稿资料不重复维护本机工具现状。
- 混淆目录 `/Users/hrygo/Documents/comfy/ComfyUI-Shared/` 只有一个误放旧文件，**所有读写只认本目录**。

## 2. 开工三件事：先定地面真相

静态配置会骗人，实测不会。

1. `pwd` + `ls` 确认当前目录。
2. `server_info` 只看 `server.running`，**不要信 `workspace.path`**（历史值，指向不存在的路径）。
3. `system_stats` 看 `system.argv` 里 `--input-directory` / `--output-directory`，那才是 live server 的真实目录。

## 3. 工具路由（硬规则）

- 跟 ComfyUI server 对话一律走 **comfy MCP 工具**（`server_info`、`search_templates`、`fetch_template`、`validate_workflow`、`run_workflow`、`job`、`fetch_outputs`、`upload_file` 等）。
- **绝不在 Bash 里调 `comfy` CLI**：不在 Bash PATH 里；用 venv 绝对路径跑也会被沙箱拦截（`PermissionError: secrets.json.lock`）。MCP server 跑在沙箱外，不受影响。
- Bash 只做：`cp` 搬文件、`python3 -I` 打 JSON 补丁（§4）、`ffprobe`/`ffmpeg` 验片。

## 4. 工作流只有两种格式，改法不同

先判别（`python3 -I -c` 看有无顶层 `definitions` 键）：

- **flat**：节点类型是 `KSampler`、`UNETLoader` 这类名字。`list_workflow_slots` / `set_workflow_slot` 可用；ACE等平面链按实际文件判别，不固定旧数量。
- **SUBGRAPH**：含 `definitions.subgraphs`，核心节点类型是一串 UUID。本目录多数图像／视频链属于此类。`slots` / `set-slot` 遇 UUID 节点必失败（且只返回无细节的 `Error executing tool`）——**失败一次就停手换路，不要重试**。

subgraph 改法：`python3 -I` 直改 JSON，同时改 `widgets_values`（按位置）和 `widgets_values_named`（按名），改完跑 `validate_workflow`，以 `valid: true` 为准。这是本目录常规操作（skill 里"禁止手改 JSON"指有正规槽位可用的情形，不适用这里）。

## 5. 模型库存 SSOT 与当前范围

- 全文SSOT：`/Users/hrygo/ComfyUI-Installs/agent-tools-setup/MODELS.md` §3；本手册不复制逐文件库存表。
- 2026-10-12实测：**23个权重文件、178,073,920,630字节、165.84 GiB**，含Qwen Image 2.1 Turbo。按目录为diffusion_models 7、text_encoders 7、vae 5、loras 2、model_patches 1、checkpoints 1。
- Qwen实际TE为Qwen3-VL 8B；两个Qwen3.5 9B仅可选提示词增强器。ACE 0.6B文本条件与4B可选语义码不互换。H3 NVFP4 TE明确CPU，Music3 BF16 TE走MPS。
- 空目录包括`embeddings/`、`upscale_models/`、`controlnet/`、`clip_vision/`、`frame_interpolation/`、`optical_flow/`。H3控制补丁实际在model_patches，不因controlnet目录空就断言没有控制能力；需要其他权重时先换方案或征得下载授权。
- 没有后置超分权重不影响原生2K。模型在库、配置引用和实际运行通过是三种不同证据。

## 6. MPS 上的两个定案（必读，`validate: true` 也拦不住它们）

1. **H3 的 video VAE 必须用 fp16 版**。官方模板默认引 int8 版，但 MPS 上 VAEDecode 报 `aten::_int_mm is not implemented`，任务直接 error。凡跑 H3，确认实例 `vae_name` 两处（`widgets_values[7]` + `widgets_values_named.vae_name`）都是 fp16。
2. **MPS不提供这些INT8/NVFP4制品的原生量化矩阵路径**。相关层解量化走浮点计算；文件压缩不保证运行峰值内存或速度优势，也不意味着一律FP32。采用方案以当前实测为准：
   - Qwen 图像：DiT/实际8B TE保持int8 + cache `int8`，PE关闭；生成基础10步，编辑官方Turbo8步，保留同尺寸回退（§13）。
   - H3 视频：DiT int8 + TE NVFP4明确CPU + video VAE fp16 + audio VAE fp32；普通FL短镜头四步优先、八步回退。四步是本机效率档，提速取决于采样、规格与实际加载状态。
   - Music3 / Controlnet：保持 bf16/fp16 原状（Music3 TE 是 8B LLM，占内存大但本机 128GB 不构成约束）。

## 7. 标准任务流程

原创整曲歌曲优先使用用户级 `song-production` Skill；宿主未加载时，先读 [歌曲创作与交付 SOP](docs/歌曲创作与交付SOP.md) 与 [执行检查清单](docs/歌曲创作执行检查清单.md)，从 [项目参数模板](docs/templates/song_project.template.json) 建立独立任务记录。短音频示例不能直接当作整曲生产配置；优先一次完整作曲，技术验收与人工试听分开记录。已有单曲实验脚本含固定输入／输出路径，未参数化前不得用于下一首歌。

1. 素材 → `cp` 到 `input/<task>.*` → `upload_file(overwrite=true)`。
2. 同类任务优先从`workflows/README.md`选`workflows/active/`当前入口，复制为`workflows/<task>.json`后改素材、prompt与seed；未覆盖的形态才`fetch_template`。验证源与冻结快照不改，旧模板保留作兼容母版。
3. 按 §4 改 JSON：LoadImage 图名、prompt（H3 动作只写"怎么动"，顺手写 Audio 段）、VAE 确认（§6）、随机 `noise_seed`、ResolutionSelector 按源图比例（方图 `1:1 (Square)`，小样 `megapixels=0.4`）。
4. `validate_workflow` 须 `valid: true`（`node_not_reachable_from_output` 等悬空节点 warning 可忽略）。
5. `run_workflow(wait=false)` 提交，**记下 `prompt_id` 立刻告诉用户**。
6. 短轮询 `job(action="status")`（§8）→ `fetch_outputs` 到 `output/<类型>/<task>/` → `ffprobe` 看规格 + `ffmpeg -ss` 抽 `preview_frame.jpg` → `Read` 验抽帧后连同成片一起呈现。

## 8. 长任务等待策略

H3 在 MPS 上是分钟级任务（内存可达 100GB+，慢正常；Music3 15 秒歌曲 `--gpu-only` 后约 1 分钟，见 §11）。
**不要 `job(action="wait")` 长阻塞**——超 MCP 传输超时会 `Request timed out`（传输层断开，不是任务失败）。正确姿势：`wait=false` 提交 + 每轮 `status` 短查。

## 9. 模板、命名、输出

- 本机无 Comfy Cloud 登录、无 API key：**只用 `api: false` 本地开源模板**，带 `API` 标签的一律不跑（除非用户明确要求先登录/充值）。
- `workflows/` 命名：`aud_` 音频 · `img_` 图像 · `h3_t2v_` H3 文生 · `vid_` H3 视频编辑 · `<task>_i2v` 一次性 I2V · `<角色>_[x_]low` / `_2k_low` / `_bright` Qwen 角色图系列 · `campfire_30s_seg*`（`_nm` = 无音乐版）多段任务。新任务沿用。
- 成片进 `output/audio/<task>/` 或 `output/video/<task>/`（图像 `output/image/<task>/`），附 `preview_frame.jpg` 抽帧方便回看。

## 10. 当前入口与历史已验证组合

当前默认／回退／可选入口见`workflows/README.md`、`workflows/active/`与`workflows/aggressive_eval/profiles.json`。9份发布副本均live validate通过，生成参数／接线与已实际运行的源等价，仅改输出前缀和展示元信息；本轮未重复渲染。输入素材与提示仍是示例，新任务必须替换。旧模板存在位置／命名镜像差异，不能只凭文件名当作当前默认。

以下是历史已验证组合，保留母版，不全线改写；I2V等当前入口未覆盖的任务可按需派生并重新校验。

- **I2V 微动**：拷 `reading_girl_i2v.json`（fl2va int8 + 32B NVFP4 + fp16 VAE + fp32 audio VAE + turbo 8 步，1:1 0.4MP 5 秒 → 640x640 24fps H.264+AAC），改图换 prompt。
- **Qwen 角色图**：`img_qwen21_low.json` 系（DiT/TE int8 + cache `int8`，10 步 0.25MP 小样）即各 `<角色>_low` 的母版；`img_qwen21_edit_low3.json` 是 25 步编辑链母版。
- **H3 文生**：`h3_t2v_low.json`（2 秒小样）/ `h3_t2v_prod.json`（5 秒 864x480）均已 DiT int8 + fp16 VAE 出片验证。
- **Controlnet**（`vid_h3_controlnet.json`）：保持 ref2va bf16 + patch bf16，需自备输入视频（上次缺 `dancer_field_pose.mp4` 未验证）。
- **Music3**（`aud_mm_music3_low.json`）：DiT fp16 + TE bf16；`aud_mm_music3_fast.json`（DiT 12 步）15 秒约 1 分钟（§11）。
- **H3 加速版**：`h3_t2v_fast.json`（TeaCache，5 秒 864x480 约 7.8 分钟，画质与基线一致）；`h3_t2v_prod.json` 与 `reading_girl_i2v.json` 已同步 TeaCache + CPU TE 补丁（§11）。

## 11. 加速优化（2026-10-11 实测定案）

- **启动参数**：`installations.json` 的 `launchArgs` 已加 `--gpu-only`（改前须完全退出 Desktop；备份 `installations.json.bak-20261011_102047`）。效果：所有 TE/VAE/intermediate 钉在 MPS，`Set vram state: SHARED` 不变（源码 594 行 MPS 强制覆盖，但不影响 `args.gpu_only` 的设备选择）。
- **Music3 9.1x**：15 秒歌 576s → 63s。根因是 AR 自回归（8B LLM 逐帧 376 次前向）原来在 CPU 跑（1.42s/it），上 MPS 后 8.12it/s。附带 DiT 30 步 → 12 步（flow matching 低步可用，`aud_mm_music3_fast.json`）。
- **H3 1.24x（DiT 1.36x）**：5 秒 864x480 从 579s → 467s。用 Icyoung 的 `ComfyUI-MiniMaxH3-TeaCache`（MIT，纯 Python，MODEL 进出，插 Switch→Guider/Scheduler 之间，`rel_l1_thresh=0.15/start=2/end=-2/total=8`），MPS 实测保质（同种子抽帧对比无漂移）。注意作者标称 3x 是 NVIDIA CMP 170HX 数据，MPS 上 8 步 turbo 只有 1.36x（步数越少缓存命中空间越小）。
- **H3 TE 必须钉 CPU**：32B TE 是 NVFP4（block scale 为 fp8），torch 2.12.1 的 MPS 后端不支持 `Float8_e4m3fn`（`torch.zeros().to(fp8)` 在 mps 直接 TypeError），`--gpu-only` 下 TE 上 MPS 会在 comfy_kitchen 反量化处炸。解法：H3 工作流的 CLIPLoader 加 `device=cpu`（`nodes.py:1036` 强制该 TE 在 CPU 加载执行），DiT/VAE 仍在 MPS。Music3 的 bf16 TE 无此问题，正常吃 `--gpu-only` 红利。
- **不要碰**：SageAttention（无 MPS 版）、torch.compile（MPS 原型阶段）、`--lowvram`/`--disable-smart-memory`（统一内存负优化）、通用 TeaCache（welltop-cn，不支持 H3）。

## 12. Qwen-Image-2.1-Turbo（2026-10-12 本机验证）

- 已新增 `models/diffusion_models/qwen_image_2.1_turbo_int8_convrot.safetensors`（7,256,787,829 字节）。基础版模型、原角色工作流及 2K 工作流保留不变。
- **实际图像编码器是 `qwen3vl_8b_int8_convrot.safetensors`**；`qwen3.5_9b_…_pe_t2i/i2i` 是可关闭的提示词增强器，不是图像生成必需的 TE。Turbo 沿用现有 TE、VAE 和 int8 KV cache；本轮关闭提示词增强。
- **官方固定时间表**：Euler、CFG=1，`ManualSigmas` 输入 `1.0, 0.978453, 0.95418, 0.926626, 0.89508, 0.845148, 0.704534, 0.414568, 0.0`。最后的零形成第 8 次更新；不要再加 shift。普通 `euler/simple/8` 不等于官方时间表。
- 已验证可跑的独立候选：`img_qwen21_turbo_official_low.json`（512 方图）、`img_qwen21_edit_turbo_official_low.json`（单参考编辑，保持输入尺寸）、`serlan_fable51_turbo_official_low.json`（640 角色小样）、`img_qwen21_character_edit_turbo_official.json`（640 角色披风换色）。官方版子图采用 `SamplerCustom + KSamplerSelect + ManualSigmas`，步数固定，不再暴露无效的 steps/scheduler 控件。
- **采用边界**：优先试用 Turbo 编辑候选，原 10 步角色生成默认不全线替换。本轮官方版单次总耗时：512 狐狸编辑 46.08s → 15.98s（约 2.88x）；640 角色披风换色 52.30s → 24.18s（约 2.16x）；640 角色生成 19.48s → 17.08s（约 1.14x）。均为日志中的 `Prompt executed in`，不是等待/轮询时间，也不是多次均值。
- 结果与运行证据：`output/image/qwen_turbo_ab/REPORT.md`、`runs.json`、`execution_evidence.log`。本轮未验证 2K、多参考、透明图、排字或 BF16/GGUF/LoRA 路线，不外推为全场景质量或速度结论。
- 本轮备份在 `workflows/backups/qwen_turbo_20261012_095405/`，含源工作流、原执行手册和 SHA-256 清单。新增官方采样版可用 `python3 -I workflows/qwen_turbo_eval/prepare_official.py <源工作流> <新文件> <输出前缀>` 复建；脚本拒绝覆盖已有文件。
- 下载工具仍可能落到旧 comfy-cli workspace；本轮发现后已把完成的模型复制到 live `models/`。后续下载必须核对返回的 `dest`，不能把下载完成当作 live server 已可加载；不要为此另起 server 或更改 Desktop 启动配置。

## 13. 当前效率路线与原生2K

工作流入口以`workflows/README.md`和profiles清单为准，active包含4份图像、3份视频、2份音频档；下面列出其验证源与一次实测，不把发布副本说成新一轮生成。

编辑active的真正参考入口是顶层LoadImage id470，换图需同步`widgets_values[0]`和`widgets_values_named.image`；对比节点自动跟随。id475为未接入旧节点，不是第二参考。当前编辑策略保持参考尺寸：2048×2048参考已实证2K，换小图后不会被未选中的width/height控件自动变成2K。正式交付逐次核对真实输出尺寸，不后置放大冒充。

- **效率优先不等于放弃2K**。正式图像保持原生目标画布；512/640仅可选预览，不经放大冒充2K。现有生产与角色2K工作流原件保留不变。
- **2K生成**：效率默认 `img_qwen21_aggressive_2k_base.json`（10步）；可选 `img_qwen21_aggressive_2k_turbo.json`（官方固定8步）。两者均实际生成2048×2048。本轮186.40s/205.54s，Turbo并未提速，但该例面部、盔甲与光盾更清晰明亮；不按Turbo名称全线替换。
- **2K编辑**：`img_qwen21_aggressive_2k_edit.json` 已跑单参考盾牌换深蓝、输出2048×2048，326.02s。`img_qwen21_aggressive_2k_edit_base.json` 同参考、prompt和seed的25步回退也已实际出片2048×2048，日志`00:17:29`（约1049s）。本次Turbo约3.22倍速度、耗时少约69%，但只是加载/缓存状态不同的单次路线对照，不是稳定均值或纯步数因果证明。两者会轻微重绘，不保证其他区域像素不变。
- **H3普通短镜头**：先用 `h3_t2v_aggressive_4step.json`，可见动作/身份/肢体缺陷时回退 `h3_t2v_aggressive_8step_nocache.json`。两路均实测864×480、124帧、24fps、实际5.167s、含音轨，均cache关闭。本轮423.36s/约630s，整任务省时约33%。NVFP4 TE明确CPU、video VAE FP16、audio VAE FP32；当前源码默认shift12/audio3，不额外加补丁。复杂动作与听感仍要验收，不宣称质量普遍等价。
- `h3_t2v_aggressive_preview_4step.json` 已实际运行验收：608×352、56帧、24fps、含32kHz双声道音轨，执行119.39s；请求2秒经帧网格实际为2.333333s。仅作可选草稿，不替代正式镜头。
- **ACE快速初稿**：`aud_ace15xl_aggressive_no_codes_continuous.json` 关闭可选codes，16s FLAC；热运行4.00s。但尾部仍有1.62s低于-50dBFS，不认证为持续满16s成品。原codes关/开对照档保留；开启版约6s低电平尾部且峰值触达0dBFS，不自动当生产回退。18.07s/8.17s的冷/热对照不能证明关闭codes更快。
- **Music3备用**：`aud_mm_music3_aggressive_12step.json` 已跑，15s请求实际14.988s、67.54s执行，44100Hz双声道FLAC，未检出-50dBFS/0.4s静音或近满幅采样。严格持续内容优先考虑此链，按实际任务匹配duration/lyrics；当前长歌词只验收短片段，不是完整歌曲，也不保证无缝循环。
- 助手不能听音频，所有音乐/视频声音的听感与歌词评价须试听。技术信号通过不是主观品质通过。
- 路线入口 `workflows/aggressive_eval/profiles.json`；证据 `output/research/aggressive_implementation_20261012/REPORT.md`、`runs.json`、`execution_evidence.log`、`FINAL_VERIFICATION.json`。11份新档均通过live validate并实际执行，最终契约验收脚本通过；ACE持续满16秒要求仍未达成，仅关闭codes路线采纳作初稿，不能把技术验收当作全部成品品质通过。
- 备份 `workflows/backups/aggressive_2k_20261012/` 含原件、SHA清单、第一版 `verified_profiles/` 历史快照及完成验收后的 `verified_profiles_v2/` 快照。7项原工作流与转换脚本未变。未下载、安装、重启、改启动参数或删模型。执行时间为单次Desktop日志，不是均值；先后加载、节点缓存不同，不把首轮筛选冒充稳定速度分布。

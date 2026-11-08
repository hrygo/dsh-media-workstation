# ComfyUI 本机多媒体工作站 · 模型与工作流（SSOT）

> 文档类型：SSOT · 状态：当前
>
> 适用范围：本机Apple M5 Max / 128 GiB / MPS，ComfyUI Desktop实例与 `~/ComfyUI-Shared/`。
>
> 最后核验：2026-10-12。库存来自共享目录逐文件字节数；环境来自Comfy MCP `server_info` / `system_stats`；运行验收来自MCP完成状态、输出媒体与Desktop执行日志。
>
> 权威边界：本文负责当前模型库存、用途、精度标称、路线选择、验收与回退。文件在库不代表已加载、所有模板可运行或作品品质通过；标称格式不等于逐层计算dtype。历史与外部数据在独立章节标注，不作为当前实测。

安装、下载与排障见 [README.md](README.md)。模型清单入口页仍为 `~/Documents/本机优化配置/docs/models/ComfyUI本机视频工作站与模型清单.md`，只保留链接，不复制库存。

## 1. 当前结论与操作入口

- **23个 `.safetensors` 文件，178,073,920,630字节 = 165.84 GiB ≈ 178.07 GB**。没有增加第二套推理服务，权重均在 `~/ComfyUI-Shared/models/`。
- **正式图像保持原生2048×2048**：基础版10步生成；Turbo官方8步优先编辑；基础版25步编辑回退。512/640仅可选预览，不放大冒充原生2K。
- **H3普通短镜头四步首选、八步回退**；当前对照档均关闭TeaCache。INT8 FL2VA DiT、NVFP4 32B TE明确CPU、视频VAE FP16、音频VAE FP32保持不变。四步属于本机效率档，不冒充上游FL8官方配置或普遍质量等价。
- **ACE仅快速音乐初稿**：关闭可选语义码，当前持续满16秒检查未通过。Music3 12步是备用链，歌词与听感仍需试听。
- 当前可直接导入的入口：[工作流索引](../../ComfyUI-Shared/workflows/README.md)、[路线清单](../../ComfyUI-Shared/workflows/aggressive_eval/profiles.json)、`~/ComfyUI-Shared/workflows/active/`。这是项目选择入口，不是Desktop自动默认或启动配置。
- 11份验证源工作流均完成live validate与实际运行。具体媒体规格、未通过项、时间口径见 [实施验收报告](../../ComfyUI-Shared/output/research/aggressive_implementation_20261012/REPORT.md) 和 [最终技术验收收据](../../ComfyUI-Shared/output/research/aggressive_implementation_20261012/FINAL_VERIFICATION.json)。

文件大小按未舍入字节数求和，再除以 `1024^3`；下表GiB保留两位小数。模型库存快照见 [inventory/state_before.json](../../ComfyUI-Shared/output/research/ssot_workflow_sync_20261012/state_before.json)。

## 2. 运行基线与边界

| 项目 | 当前值 | 证据／边界 |
|---|---|---|
| 部署 | ComfyUI Desktop standalone | `deploy_environment=local-desktop2-standalone`；进程由App管理 |
| 后端／前端 | 0.39.2／1.53.10 | `system_stats` |
| PyTorch／Python | 2.12.1／3.13.12 | live server；与comfy MCP自身Python不同 |
| 硬件／后端 | Apple M5 Max、128 GiB统一内存、MPS | `system_stats`；空闲内存随任务变化，不登记为固定预算 |
| API | `http://127.0.0.1:8188` | 本机回环；8000属oMLX |
| 程序／共享数据 | `~/ComfyUI-Installs/ComfyUI/`／`~/ComfyUI-Shared/` | Desktop分离布局 |
| 输入／输出 | `~/ComfyUI-Shared/input`／`output` | live `system.argv` 的对应启动参数 |
| 启动策略 | 现有 `--gpu-only` | H3 TE单独明确CPU；本轮不改启动参数 |
| comfy-cli | 1.22.0 | `server_info`；与server交互走MCP，不在agent Bash跑CLI |

`server_info.workspace.path` 仍指向旧 `~/Documents/comfy/ComfyUI`，不用于定位数据，不据此另起server。共享目录不是comfy-cli project/1，不初始化工程。当前同步没有采集队列状态，不沿用历史“0/0”作当前断言。

## 3. 当前模型库存与用途

### 3.1 MiniMax H3视频／音频（8）

| 子目录 | 模型文件 | 用途与配套 | 标称格式 | GiB |
|---|---|---|---|---:|
| diffusion_models | `minimax_h3_fl2va_pruned_int8_convrot.safetensors` | FL视频／配套音频主模型；文生、首帧／首尾帧路线；当前四／八步档使用 | INT8 ConvRot | 19.53 |
| diffusion_models | `minimax_h3_ref2va_pruned_bf16.safetensors` | 参考条件视频生成／编辑主模型，现有ControlNet路线使用；未闭环验收 | BF16 | 37.46 |
| text_encoders | `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | H3文本／多模态条件编码器；`CLIPLoader device=cpu` | NVFP4 AWQ | 14.61 |
| vae | `minimax_h3_video_vae_fp16.safetensors` | 视频帧潜空间编解码；MPS已验证版本 | FP16 | 4.85 |
| vae | `minimax_h3_audio_vae_fp32.safetensors` | 配套音轨潜空间编解码 | FP32 | 0.56 |
| loras | `minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors` | FL少步蒸馏适配器；本机同款下已试四／八步，不把四步命名为上游官方FL8 | BF16 | 1.82 |
| loras | `minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors` | Ref路线四步适配器，不与FL LoRA直接互换 | BF16 | 1.82 |
| model_patches | `minimax_h3_fun_controlnet_union_pruned_bf16.safetensors` | H3结构／动作控制补丁，配合参考路线 | BF16 | 3.93 |

### 3.2 Qwen Image 2.1图像（5）

| 子目录 | 模型文件 | 用途与采用方式 | 标称格式 | GiB |
|---|---|---|---|---:|
| diffusion_models | `qwen_image_2.1_int8_convrot.safetensors` | 基础生成／编辑DiT；原生2K生成默认10步，编辑25步回退 | INT8 ConvRot | 6.76 |
| diffusion_models | `qwen_image_2.1_turbo_int8_convrot.safetensors` | 蒸馏生成／编辑DiT；官方固定8步，优先2K编辑，生成细节可选 | INT8 ConvRot | 6.76 |
| text_encoders | `qwen3.5_9b_qwen_image_2.1_pe_t2i.int8_convrot.safetensors` | 可选文生图提示词增强器，不是实际图像TE；当前效率档关闭 | INT8 ConvRot | 8.82 |
| text_encoders | `qwen3.5_9b_qwen_image_2.1_pe_i2i.int8_convrot.safetensors` | 可选编辑提示词增强器，不是实际图像TE；当前效率档关闭 | INT8 ConvRot | 8.82 |
| vae | `qwen_image_2.1_vae_bf16.safetensors` | 图像潜空间编解码，基础版与Turbo共用 | BF16 | 0.63 |

**实际图像TE为§3.5的Qwen3-VL 8B**，基础版和Turbo共用；不能把两个9B PE模型写成生成必需的TE。Turbo文件为7,256,787,829字节，基础版与既有2K／角色模板仍保留。

### 3.3 ACE-Step 1.5 XL Turbo快速初稿（4）

| 子目录 | 模型文件 | 用途与限制 | 标称格式 | GiB |
|---|---|---|---|---:|
| diffusion_models | `acestep_v1.5_xl_turbo_bf16.safetensors` | 音乐／歌曲扩散主模型，低步数生成 | BF16 | 9.29 |
| text_encoders | `qwen_0.6b_ace15.safetensors` | 文本条件编码器；不是4B语义码LM的可互换小号版本 | BF16 | 1.11 |
| text_encoders | `qwen_4b_ace15.safetensors` | 可选自回归语义码LM；`generate_audio_codes=false`跳过该生成环节，不表示所有文本编码或LM驻留都消失 | BF16 | 7.80 |
| vae | `ace_1.5_vae.safetensors` | ACE音频潜空间编解码 | BF16 | 0.31 |

四件套BF16已有历史文件头核验。XL Base／AIO模板仍需当前库存中不存在的主权重，不因共用TE／VAE而就绪。当前16秒容器不等于16秒持续内容，验收限制见§6。

### 3.4 MiniMax Music 3备用音乐链（3）

| 子目录 | 模型文件 | 用途与设备 | 标称格式 | GiB |
|---|---|---|---|---:|
| diffusion_models | `minimax_music3_dit_fp16.safetensors` | 音乐／歌曲扩散主模型；当前12步 | FP16 | 4.58 |
| text_encoders | `minimax_music3_text_encoder_pruned_bf16.safetensors` | 描述／歌词条件及自回归环节；现有`--gpu-only`下走MPS，不是CPU | BF16 | 15.56 |
| vae | `minimax_music3_dav.safetensors` | DAV音频编解码器；已有文件头核验为FP32 | FP32 | 0.20 |

### 3.5 实际图像TE与姿态工具（3）

| 子目录 | 模型文件 | 用途 | 标称格式 | GiB |
|---|---|---|---|---:|
| text_encoders | `qwen3vl_8b_int8_convrot.safetensors` | Qwen Image基础版／Turbo的实际文本与视觉条件编码器 | INT8 ConvRot | 8.71 |
| checkpoints | `sdpose_wholebody_fp16.safetensors` | 全身姿态关键点估计，用于制作控制输入；不是普通文生图checkpoint | FP16 | 1.79 |
| diffusion_models | `rt_detr_v4-x-hgnet_fp16.safetensors` | 姿态链的检测辅助模型，定位目标区域；不是生成模型 | FP16 | 0.12 |

格式统计：**BF16 10、INT8 ConvRot 6、FP16 4、FP32 2、NVFP4 AWQ 1，合计23**。其中6个是主生成模型，其余是条件编码、编解码、LoRA或控制／检测辅助。

### 3.6 库存、引用与保留边界

- 当前没有独立超分、补帧、光流等模型权重；`upscale_models/`、`frame_interpolation/`、`optical_flow/` 等为空。原生2K不依赖后置超分。
- Ref2VA、控制补丁、Ref LoRA、SDPose、RT-DETR五件共约45.12 GiB，为现有ControlNet方向保留；`vid_h3_controlnet.json`尚未出片闭环，不因单引用自动删除。
- 引用扫描必须区分直属旧／验证档、`active/`发布入口、`aggressive_eval/`中间源和`backups/`历史快照。JSON包含文件名只说明配置引用，可能是关闭或死分支，不证明加载执行；0引用也不自动构成删除授权。
- **Historical，非当前库存**：2026-10-11 H3 BF16 TE 47.97 GiB与下载残留经trash清理；旧BF16 DiT／Qwen 8B BF16等不在当前目录。本文不复核trash内容、不恢复或删除模型。

## 4. MPS兼容性与设备规范

### 4.1 不从存储格式推断计算或加速

MPS上这些INT8／NVFP4制品没有对应原生量化矩阵路径；相关层解量化后走浮点计算。`full_precision_mm`不等于一律FP32，`system_stats`也不报告逐层dtype。压缩权重与运行峰值内存不能简单按文件大小推算，量化名称不证明提速。

当前保留Qwen/H3 INT8制品和已验证浮点回退，不因理论精度偏好重下载整套BF16。速度与品质按具体模型、采样、分辨率、设备和实际出片评价；Music3、控制补丁、ACE保留已有浮点制品。

### 4.2 H3固定兼容配置

- `qwen3vl_32b_minimax_h3_nvfp4_awq` 的CLIPLoader显式 `device=cpu`；合法控件值为`default`／`cpu`，不存在`mps`。现有`--gpu-only`下`default`会解析到MPS，不能误用。
- 视频VAE必须 `minimax_h3_video_vae_fp16`；INT8视频VAE曾在MPS解码失败，validate通过不能拦截运行时算子错误。
- 音频VAE为FP32。DiT与VAE仍走MPS，TE CPU例外不要求重启或取消`--gpu-only`。
- 位置值、`widgets_values_named`、promoted输入及真实link优先级须对齐；不能仅改死值或以一处看似正确代替实际接线。

### 4.3 H3 TE历史选型证据（Historical）

2026-10-11的负结果支持继续保留NVFP4＋CPU，而不是改用47.97 GiB BF16 TE。两次任务为不同提示词／加载状态，不是完美控制变量实验，不把比值写成固定因果收益。

| 路线 | 历史执行时间 | 证据与限制 |
|---|---:|---|
| NVFP4 TE＋CPU，8步＋TeaCache | 466.69s | Desktop日志与历史任务输出 |
| BF16 TE＋默认MPS | 约840s | 比值约1.80；加载与统一内存压力是解释线索，不是新实测隔离结论 |

NVFP4直接走MPS曾因`Float8_e4m3fn`失败。官方／社区配对资料支持该组合，但外部LPIPS、SSIM、flicker数字不是本机复测，也不证明所有任务质量等价。详细旧证据随修改前MODELS.md备份保留。

### 4.4 Qwen、ACE与Music3规范

- Qwen：实际8B TE、INT8 KV cache，PE关闭为效率默认。基础与Turbo共用TE／VAE；不默认改INT4/BF16/GGUF。
- ACE：0.6B文本条件与4B可选语义码分工不变；DiT CFG与文本节点LM CFG不同，不互相代替。
- Music3：BF16 TE在MPS执行；历史15秒链从576.25s到63.24s的改善来自设备与低步数策略，不能写成TE当前仍CPU。
- 不采用SageAttention、实验性MPS torch.compile、lowvram或关闭smart-memory作为本机当前优化。

## 5. 采样、规格与工作流编辑契约

- **Qwen Turbo官方采样**：Euler、CFG1，ManualSigmas为`1.0, 0.978453, 0.95418, 0.926626, 0.89508, 0.845148, 0.704534, 0.414568, 0.0`。末尾零形成第8次更新，不另加shift；`euler/simple/8`不是同一时间表。
- **H3**：`res_multistep/simple`，源码默认video shift12／audio shift3，不重复叠加。上游FL Turbo标准8步，Ref Turbo标准4步；本机FL四步是独立验收的效率候选。
- **H3帧网格**：`17k+5`；5秒请求输出124帧／24fps约5.167秒，2秒预览输出56帧／24fps约2.333333秒。不要把容器时长强写为精确请求值。
- **正式图像**：原生2048×2048；预览不自动取代正式交付。编辑沿用2K参考，resolution=0保持输入尺寸，不后置放大冒充原生生成。
- **格式修改**：flat使用slots；UUID subgraph按项目AGENTS.md用Python `-I`同步位置／命名值与link，改后live validate。slots在UUID失败一次即换路，不重复试。
- **执行**：Comfy MCP提交`wait=false`，立即报告prompt_id，短查status；不用长wait、raw HTTP或Bash comfy。完成后fetch、媒体规格／抽帧／信号检查；不能听音频时不宣称听感通过。

## 6. 当前工作流选择与验收

### 6.1 路线与一次实测

| 用途 | 已运行的验证源 | 实测规格／执行时间 | 采用边界 |
|---|---|---|---|
| 原生2K生成默认 | `img_qwen21_aggressive_2k_base.json` | 2048²；186.40s | 基础10步，效率默认 |
| 原生2K生成可选 | `img_qwen21_aggressive_2k_turbo.json` | 2048²；205.54s | 该例更明亮清晰，但不更快 |
| 原生2K编辑默认 | `img_qwen21_aggressive_2k_edit.json` | 2048²；326.02s | 官方Turbo8步；轻微重绘 |
| 原生2K编辑回退 | `img_qwen21_aggressive_2k_edit_base.json` | 2048²；日志00:17:29，约1049s | 同参考／prompt／seed的基础25步，已运行 |
| 普通短镜头默认 | `h3_t2v_aggressive_4step.json` | 864×480／124帧／24fps／音轨；423.36s | 动作／身份缺陷时回退 |
| 视频回退 | `h3_t2v_aggressive_8step_nocache.json` | 同规格；日志00:10:30，约630s | 非普遍质量等价证明 |
| 可选视频预览 | `h3_t2v_aggressive_preview_4step.json` | 608×352／56帧／24fps／音轨；119.39s | 已运行；不替代正式镜头 |
| 音乐初稿 | `aud_ace15xl_aggressive_no_codes_continuous.json` | 16秒FLAC；热运行4.00s | 末尾仍1.625秒低电平，仅初稿 |
| 音乐备用 | `aud_mm_music3_aggressive_12step.json` | 实际14.988秒；67.54s | 技术信号通过，长歌词仅短片段 |

另保留ACE原始codes关／开对照：18.07s／8.17s，分别尾部约2.25／6.01秒低电平；开启版峰值0dBFS、1048个近满幅采样，不作为自动生产回退。近满幅计数不是单独的削波证明。

时间来自Desktop `Prompt executed in`，不含排队／轮询。2K编辑本次1049／326.02约3.22倍速度、省时约69%；H3四／八步本次约省33%。均为加载／缓存状态不同的单次路线对照，不是多次均值或纯步数／codes开关因果证明。

### 6.2 当前入口、旧模板与验证来源

当前扫描：workflows直属72份JSON、active发布9份JSON、直属5份.bak（含原3份TE回退前备份）。不把备份／中间源计入当前入口；[引用扫描收据](../../ComfyUI-Shared/output/research/ssot_workflow_sync_20261012/reference_scan.json)单列直属与active引用。引用包括死分支，不等于实际加载。

9份active均通过本轮本机live validate，0错误；两份编辑各一个不可达LoadImage warning，服务剪枝、无执行影响。生成参数等价检查通过，没有付费API节点；[发布收据](../../ComfyUI-Shared/output/research/ssot_workflow_sync_20261012/active_publication.json)记录各源SHA、MCP源prompt_id与本轮校验结果。

- 当前发布入口在 `workflows/active/`，工作流索引在`workflows/README.md`。由上述已运行源制作，采样、模型、输入提示与seed保持；输出前缀改为长期目录，避免继续使用测试批次名称。发布副本需单独live validate；其运行证据来自参数等价源，不假称副本已重新渲染。
- 11份验证源、`aggressive_eval/`助手脚本及第一次／第二次冻结快照保留。旧角色、低分辨率、I2V、TeaCache模板不全线替换；旧模板名称不等于当前默认。
- I2V微动仍有已验证的`reading_girl_i2v.json`组合；ControlNet、XL Base和AIO等未闭环或缺权重模板不在当前默认入口中。
- 新任务复制当前入口并修改素材、prompt、seed和输出名，再validate；2K编辑随附参考仍是演示盾牌图，不会自动替换成用户素材。

### 6.3 验收边界

- 11份源的MCP完成记录、4份2048² PNG、3份视频规格及设备／VAE兼容条件已核验；7项旧工作流／转换器哈希未变。
- ACE持续满16秒要求未通过；不通过截尾、补循环或改增益掩盖。关闭codes路线仅初稿，开启对照不采纳。
- 图像编辑不是区域外像素不变认证；六帧视频检查不是全帧／精确分镜／声音同步认证。
- 助手不能听音频；Music3歌词、音乐性、意外人声、发音和无缝循环未主观验收。

## 7. 成品与证据入口

- [原生2K与H3／音乐实施报告](../../ComfyUI-Shared/output/research/aggressive_implementation_20261012/REPORT.md)
- [完整11份运行记录、prompt_id、参数与输出SHA-256](../../ComfyUI-Shared/output/research/aggressive_implementation_20261012/runs.json)
- [最终技术验收收据](../../ComfyUI-Shared/output/research/aggressive_implementation_20261012/FINAL_VERIFICATION.json)
- [2K图像结果与原图](../../ComfyUI-Shared/output/research/aggressive_implementation_20261012/IMAGE_RESULTS.md)
- [512／640 Turbo历史对照](../../ComfyUI-Shared/output/image/qwen_turbo_ab/REPORT.md)；不直接外推2K
- [第一版历史冻结清单](../../ComfyUI-Shared/workflows/backups/aggressive_2k_20261012/verified_profiles/sha256.json)与[第二版完成验收冻结清单](../../ComfyUI-Shared/workflows/backups/aggressive_2k_20261012/verified_profiles_v2/sha256.json)

直出图像、视频、音频分别在`output/image`、`output/video`、`output/audio`；角色、campfire多段、字幕及评分历史产物全部保留。输出文件总数随预览、复制与报告增加，不用旧137个文件作为当前库存指标。

## 8. 历史与外部路线（非当前默认）

- **Historical**：原8步＋TeaCache任务曾为466.69s；NVFP4／BF16 TE两次不同场景任务为466.69／约840s。详细原日志、表格与上游佐证在修改前SSOT备份，不能当作新路线受控基准。
- **外部、未本机复测**：`appautomaton/mlx-h3`与MLX-Gen是独立运行栈，MLX量化不是Comfy INT8 ConvRot／NVFP4；safetensors只是容器，不可跨框架直接套用。没有在本机安装、迁移或测速，不把作者报告写成本机能力。
- **许可边界**：MiniMax H3及派生权重保留上游Community License；地域／单独授权规则以实际模型卡和授权为准。安装或运行记录不代替授权，本轮不新增许可判断或改变运行地点。

## 9. 维护与回退

1. 模型变化先扫描真实共享目录、计算未舍入字节总量，更新§3／格式统计与README Q7；不把下载完成等同于live目录就绪。
2. 修改工作流先备份、同步控件与link、validate；设备、精度、采样或生成参数变化需新的实际出片，不从同名模型或图校验外推。
3. 当前入口的发布检查应核对源SHA、允许差异、引用权重／素材、live validate结果和路线清单。仅输出命名／展示元信息变化须明确标注继承源运行证据。
4. 按任务使用同规格回退档；不自动降低正式2K，不默认启用PE或追加采样步数，不下载、删除、重启或改启动配置来“同步文档”。
5. 第一／第二版冻结快照不覆盖；本轮同步前后文件、索引与验证收据另存独立备份。回退只恢复清单中的指定文件，不触碰模型和成品。
6. SSOT只收文本；权重和成品不出仓。索引页不复制库存，已同步管理文档改源文件，不重复手动入库。

## 10. 权威引用

- 当前本机事实：Comfy MCP `server_info`／`system_stats`、共享模型目录字节清单、上述11份运行和媒体证据；核验2026-10-12。
- 本机执行规范：`~/ComfyUI-Shared/AGENTS.md`；UUID工作流例外、MPS兼容配置与异步执行以该规范为准。
- 上游：[Qwen Image 2.1 Turbo](https://huggingface.co/Qwen/Qwen-Image-2.1-Turbo)、[MiniMax H3模型卡](https://huggingface.co/MiniMaxAI/MiniMax-H3)、[Comfy-Org H3制品](https://huggingface.co/Comfy-Org/MiniMax-H3)、[ComfyUI H3流程](https://docs.comfy.org/tutorials/video/minimax/minimax-h3)。链接是规格参考，不是此次新外网复测。
- 历史TE参考：[MiniMax官方集成指引](https://github.com/MiniMax-AI/awesome-minimax-h3-integration)、[6block NVFP4配对实验](https://huggingface.co/6block/MiniMax-H3-Qwen3-VL-NVFP4)；作者数据非本机复测。

# 04 SOP：ComfyUI 生成

## 工作流清单（workflows/active）

9 份全部在本机 live validate 通过（comfy-cli 1.22.0 / ComfyUI 0.44.2 / MPS）。均为前端图格式，部分含 UUID subgraph，工具会自动转换。

| 文件 | 用途 | 关键模型 | 主要参数 |
|---|---|---|---|
| img_default_2k.json | 文生图 基础档 | qwen_image_2.1_int8_convrot + qwen3.5_9b_pe_t2i + vae_bf16 | 2048x2048，10 步，cfg 1.0 |
| img_detail_2k.json | 文生图 细节档 | qwen_image_2.1_turbo_int8_convrot | turbo 变体，步数更高 |
| img_edit_default_2k.json | 图生图/编辑 默认 | qwen_image_2.1_turbo_int8（i2i）+ LoadImage/ImageCompare | 2048²，8 步 |
| img_edit_fallback_2k.json | 图生图/编辑 回退 | qwen_image_2.1_int8（非 turbo） | 步数更高，慢但稳 |
| h3_t2v_default.json | 文生视频 四步 | minimax_h3 fl2v_turbo_8step + fl2va_int8（TE 明确 CPU） + video_vae_fp16 + audio_vae_fp32 | 4 步优先 |
| h3_t2v_fallback.json | 文生视频 八步回退 | 同上 | 8 步，质量回退档 |
| h3_t2v_preview.json | 文生视频 预览 | 同上 | 小规格预览 |
| aud_mm_music3_default.json | 音乐 MiniMax Music3 | music3_dit_fp16 + text_encoder_pruned + dav | 12 步，备用链 |
| aud_ace15xl_draft.json | 音乐 ACE-Step 1.5 快速初稿 | acestep_v1.5_xl_turbo_bf16 + qwen 0.6b/4b TE + ace_1.5_vae | 快速初稿，16s 检查未过 |

全部 18 个权重文件在本机 ~/ComfyUI-Shared/models（合计 167 GiB），本仓不入库。

## 运行循环

1. 预热检查

       system_stats            # 看 vram_free；重模型串行，不并跑
       server_info             # 确认 running 与 comfy-cli 版本

2. 复制母版到任务目录（不改 active 母版）

       cp ~/ComfyUI-Shared/workflows/active/img_default_2k.json <project>/workflows/

3. 静态校验（无 VRAM 消耗）

       validate_workflow(workflow_path=<project>/workflows/img_default_2k.json)

4. 看参数地址

       list_workflow_slots(...)  → 例如 459.prompt / 459.steps / 459.width
       set_workflow_slot(overrides=[{address:"459.prompt", value:"..."}], stdout=false)

   stdout=false 才会写回文件；默认只回显。

5. 提交（异步，先拿 id）

       run_workflow(workflow_path=..., wait=false)  → prompt_id

   立即记录 prompt_id、工作流路径、关键参数到 project.json。

6. 等待与取件

       job(action="wait", prompt_id=..., timeout_seconds=...)   # 或 status 轮询
       fetch_outputs(prompt_id=..., out_dir=<project>/assets)

7. 验收

       ffprobe / media_probe 核对真实宽高、帧率、时长、音轨
       图像另存 previews/ 抽看

## 纪律

- 断线、超时、状态未知：先按原 prompt_id 查状态，禁止自动重投。
- 取消只针对已核实属于本任务的 prompt_id，不清空队列。
- 不自动安装节点、不自动下载权重、不用付费云节点。
- 不做「小样直接当正式」：视频先预览档，用户认可再跑正式档。
- 母版只在 active 里维护；任务目录里的副本可随意改。

## 容量与时间口径

| 工作 | 本机实测/标称 | 备注 |
|---|---|---|
| 2K 文生图（10 步） | 分钟级 | MPS，9B TE + int8 DiT |
| 2K 图生图（8 步 turbo） | 分钟级 | 编辑优先 turbo |
| H3 视频（4 步） | 数分钟起，随分辨率/帧数上升 | TE CPU、video VAE FP16 不变 |
| Music3（12 步） | 分钟级 | 歌词与听感需试听 |
| ACE 1.5 初稿 | 最快 | 仅初稿，持续 16s 检查未过 |

标称格式不等于逐层计算 dtype；不要用文件名推断速度。

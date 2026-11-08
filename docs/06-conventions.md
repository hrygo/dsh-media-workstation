# 06 规约：目录、资源、隐私、边界

## 目录

    ~/ComfyUI-Shared/
      input/                     ComfyUI 输入（上传素材放这里）
      output/                    ComfyUI 生成物（collect 的来源）
      models/                    权重（167 GiB，不入库）
      workflows/active/          发布母版工作流（只在这里维护）
      projects/<项目名>/
        input/                  本项目原始输入（只读）
        workflows/              从 active 复制的任务副本
        assets/                 入库的片段/图片/音频
        artifacts/              edit_decisions、SRT、混音件、清单
        renders/                成片
        previews/               抽帧、预览
        project.json            记账

项目名必须唯一；写文件默认不覆盖。

## project.json 必填

- spec：目标宽高、帧率、音频规格、响度目标
- inputs：素材来源
- toolchain：ffmpeg / comfy-cli / SpeechRail profile 版本
- workflows：工作流路径与哈希或版本
- params：seed、steps 等主要参数
- job_ids：comfy prompt_id、speechrail job id
- outputs：产物路径
- acceptance：technical 与 manual_pending 分开

不写凭据、不写完整模型列表、不贴 base64。

## 资源与并发

- 先查共享队列（job action=queue），保留别人的任务
- 重推理同一时刻一路：ComfyUI、SpeechRail、ImageHive 串行
- 提交前看 vram_free；不看就提交容易 OOM 把整个 ComfyUI 进程带走
- 视频先预览档；2K 图不用 512 冒充

## 隐私与上下文

- 本地推理 ≠ 对话离线：素材与文本是否出网取决于当前对话模型路由
- 敏感素材（人像、客户资料）先确认路由；不确定就先问
- 不要把整份工作流 JSON、完整节点列表、base64 媒体反复打印进上下文

## 边界（先说明影响与回退，再征求意见）

- 不自动安装节点、不自动下载/删除权重
- 不启动云或付费节点
- 不上传素材到外部
- 不重启/停止 ComfyUI、不清空队列、不自动卸载模型
- 不改 MPS 与内存策略

## 验收分离

| 类型 | 手段 | 谁来判断 |
|---|---|---|
| 技术 | ffprobe / probe 断言 / 抽帧 | 可以自动化 |
| 听感 | 人耳 | 必须人工 |
| 音乐性 | 人耳 | 必须人工 |
| 口型 | 逐段比对 | 必须人工 |
| 版式审美 | 人眼 | 必须人工 |

技术断言全过只说明文件是合法的，不说明内容可用。

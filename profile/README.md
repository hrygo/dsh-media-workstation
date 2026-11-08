# DSH 本机影音工作台

独立 profile：`media`。默认 preset：`media`（PTC + 按需工具发现）。只在此 profile 注册 ComfyUI、SpeechRail、ImageHive，FFmpeg/FFprobe 经 bash 使用。

## 启动

在终端执行：

```sh
cd "$HOME/ComfyUI-Shared"
dsh --profile media
```

默认仅监听 `127.0.0.1:3088`，启动时打开带本机授权信息的页面。无须自动打开浏览器时：

```sh
dsh --profile media --no-open
```

不要分享启动日志中的认证 URL。停止当前实例使用原终端 Ctrl-C；已有 3088 实例时不要重复启动。Desktop 继续使用原来的桌面应用，不把 `media` 当作 Electron profile 切换器。

## 工具与操作

- ComfyUI：复用正在运行的 Desktop 实例，独立 comfy-mcp 前端；不启动第二套模型服务。
- SpeechRail：首次 describe；同步 ASR/TTS 和持久任务 readiness 分开判断。
- ImageHive：复用既有 daemon 与 DSH 协议 adapter。
- FFmpeg：先 ffprobe，输出使用新文件和 `-n`；原素材保持只读。
- 首次任务加载 `media-workbench` 技能，按需加载 `speechrail`；工具先搜索、下一次 run_code 调用。

## 文档与验收

- [深度定制方案](docs/CUSTOMIZATION.md)：工具分工、上下文、资源、长任务、品质与后续优化。
- [实施步骤](docs/IMPLEMENTATION_PLAN.md)。
- [验收记录](docs/ACCEPTANCE.md)：实测、未测与服务限制。

## 配置与回退

分离前最新配置备份：`/Users/hrygo/.dsh/backups/media-separation-final-20261018T003504Z`；首轮14份原始备份继续保留。备份目录含既有配置和SHA-256清单，可能含凭据，禁止公开。

本次只更改通用 Desktop 的 manifest / patch；原安装依赖、模型与全局配置保留。回退先停止本次 media 实例，检查并行变更：

```sh
python3 "$HOME/.dsh/profiles/media/checks/restore.py" --check
python3 "$HOME/.dsh/profiles/media/checks/restore.py" --apply
```

恢复脚本只在当前配置哈希匹配本次修改后快照时恢复；存在后续改动即拒绝覆盖。恢复后新建通用会话；如旧会话仍保留旧工具，等待现有工作结束后重开应用。media profile 和本次验收文件保留，回退不删除模型或成品。

# Media Profile 本机验收

核验日期：2026-10-18。状态：**已完成 media 接入和其他 profile 的影音工具分离。**

## 已实施

media 使用独立 Web profile、默认 media preset、固定 PTC Tool Search 0.1.1、三个影音 MCP 和 media-workbench / speechrail 两技能。FFmpeg / FFprobe 经 bash 使用。
Desktop 移除 SpeechRail / ImageHive MCP、image-gen 配置和 dsh-image-gen bundle，保留安装制品供回退；默认模型、工具搜索升级与其他非影音配置保留其最新状态。web / sdk / headless 无影音 MCP，不需改写；全局 Hindsight配置不变。

## 实测结果

| 检查 | 结果 |
|---|---|
| media profile 实际启动 | 通过，127.0.0.1:3088 |
| 浏览器界面 | 前轮同一media配置显示默认media preset和模型选择；未发模型请求 |
| 影音MCP注册 | 63项：ComfyUI、SpeechRail、ImageHive |
| PTC按需发现 | 初始run_code / tool_search，发现后在下一程序中调用成功 |
| MCP只读调用 | ComfyUI server_info / system_stats、SpeechRail describe、ImageHive model_status 成功 |
| 技能目录 | media-workbench / speechrail 可发现 |
| FFmpeg沙箱执行 | workspace-write、full enforcement、exitCode=0 |
| FFprobe | 320×180、24fps、1.000秒、H.264视频 / AAC音轨 |
| 分离后通用配置实际启动 | 无影音工具；22项编码/数据库MCP及Hindsight仍可发现 |
| web / sdk / headless最终组合 | 均无影音MCP |
| 备份与回退 | 5份最新备份SHA-256通过；隔离夹具中的check、apply和拒绝后续改动均通过 |

最终收据目录：`/Users/hrygo/.dsh/profiles/media/checks/final-20261018T003521Z`。media-runtime.json、general-runtime.json为实际注册和调用结果；ffmpeg-smoke.mp4为测试片。checks/profile-isolation.json记录其他profile组合；checks/summary.json为摘要；checks/changes.json记录本任务仅两处Desktop变更。

通用验收实例使用最新Desktop配置的只读副本与现有安装依赖，独立DSH_HOME、端口3089；未重启实际Desktop。该副本仍有better-sidebar缺少dsh-settings的导入警告，不阻断工具隔离验收；本次不修复该UI插件，也不声称全部Desktop UI插件已通过。

移除影音项后，其他操作继续更新Desktop的模型选择与PTC Tool Search bundle，本任务保留这些后续变更、不再写回Desktop。恢复脚本在检测到这些后续变化时会拒绝整文件恢复，这是保护行为；需要实际回退时应先合并后续非影音修改。不要使用旧备份覆盖最新配置。

## 限制

SpeechRail ASR/TTS/diarization readiness=true，但jobs.spool_ready=false、runner_active=false；持久任务未就绪，不承诺跨重启恢复。
未提交ComfyUI / ImageHive生成、配音或转写，未清队列、下载模型或重启模型服务；FFmpeg仅使用合成源。未运行真实LLM对话或视觉输入，继承的模型声明为text，不能承诺模型看图；真实成片、听感、音乐性和口型仍需项目验收。profile不隔离共享资源。

旧会话可能保留原composition或工具发现记录；分离后的新启动、新会话不再注册影音工具。无需强行中断活动任务，必要时任务结束后重开应用。

## 备份与操作

本次最新备份：`/Users/hrygo/.dsh/backups/media-separation-final-20261018T003504Z`（5份当前配置及SHA-256清单），首轮14份备份也保留。restore.py只允许恢复本次两个目标文件，并严格拒绝后续改动；不会删除media、权重或成品。启动和回退命令见README.md，深度定制方案见CUSTOMIZATION.md。

本次只改仓库外本机配置，使用已安装发行运行时验收，未运行仓库构建或全量测试。

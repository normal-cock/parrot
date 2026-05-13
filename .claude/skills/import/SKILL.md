---
name: import
description: 导入YouTube视频素材，生成视频、音频、字幕等资源文件
---

用户需要提供两个参数：
- `url`: YouTube 视频的 URL
- `name`: 资源目录名称（同时也是所有生成文件的前缀，如 `item`）

运行以下命令完成素材导入：

```bash
bash /data00/repos/parrot/.claude/skills/import/scripts/import.sh {{url}} {{name}}
```

该脚本会在 `data00/repos/parrot/tmp/{{name}}/` 下生成以下资源文件：

**视频相关：**
- `{{name}}-raw.mp4` — 下载的原始视频（480p，通过 ytdown.io）
- `{{name}}.mp4` — 标准化音量后的视频
- `{{name}}.mp3` — 提取的音频文件
- `{{name}}.m3u8` + `ts_file/` — HLS 流媒体分片

**字幕相关（通过浏览器 + API 自动下载）：**
- 使用 browse CLI 打开 downsub.com 完成 Cloudflare Turnstile 验证
- 捕获 Turnstile token，通过 API 下载英文字幕 SRT
- `{{name}}-raw.srt` — 原始英文字幕
- `{{name}}-raw.vtt` — 原始英文字幕（UTF-8编码）
- `{{name}}-e.vtt` — 英文版字幕
- `{{name}}-c.vtt` — 中文翻译字幕

**前置条件：**
- browse CLI 可用（`npm install -g @browserbasehq/browse-cli`）
- 代理服务运行在 127.0.0.1:1081

如果用户没有提供 url 或 name，主动询问缺失的参数。

> **修改本 skill 前**，必须先阅读 `NOTES.md` 了解历史踩坑记录和设计决策。

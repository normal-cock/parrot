# Import Skill 开发笔记

## ytdown.io 视频下载

- API 流程：`POST app.ytdown.to/proxy.php` → 获取 mediaItems → 选 480p (854x480) → GET mediaUrl 解析下载地址 → 下载视频
- ytdown 后端处理视频需要时间，第一次 GET mediaUrl 可能返回 "Waiting..." 或 "In Processing..."，需要轮询重试（最多 5 次，间隔 3s）
- mediaUrl 返回值可能是 JSON（含 fileUrl）也可能是纯文本 URL，需要兼容两种格式
- 必须走代理 127.0.0.1:1081，否则 ytdown.io 可能无法访问

## downsub.com 字幕下载

- **为什么需要浏览器**：downsub.com 有 Cloudflare Turnstile 验证，必须通过真实浏览器完成验证后才能调用 API
- **为什么浏览器下载按钮不产生本地文件**：`browse env local` 启动的隔离 Chrome 没有配置 `Browser.setDownloadBehavior` CDP 命令，Preferences 中没有下载目录，点击下载后文件被静默丢弃
- **解决方案**：浏览器仅用于完成 Turnstile 验证，然后从网络捕获 (`/tmp/browse-default-network/`) 中提取 POST `get.downsub.com` 的请求体（包含加密的 Turnstile token），用 Python requests 通过代理直接调用 API 下载 SRT
- API 流程：浏览器完成 Turnstile → 捕获 `POST get.downsub.com` 的请求体 `{url, data}` → 用 requests POST 获取字幕列表 → GET `subtitle.downsub.com/srt/{token}` 下载 SRT
- downsub 的 `get-info.downsub.com` API 在隔离 Chrome 中会报 `net::ERR_FAILED`（非 Cloudflare 拦截，是隔离环境的通用网络问题），这不影响主流程
- SRT 文件编码可能不是 UTF-8，下载后需要做一次 UTF-8 转换

## 代理

- 代理函数 `proxy_on` / `proxy_off` 定义在 `~/.bashrc` 中，脚本通过 `eval "$(sed ...)"` 加载
- Python 脚本需要在 requests.Session 上设置 `proxies = {'http': 'http://127.0.0.1:1081', 'https': 'http://127.0.0.1:1081'}`
- 部分操作（如 ffmpeg、make 本地命令）不需要代理，只在网络请求时开启

## 脚本设计原则

- 每一步都检查输出文件是否已存在，存在则跳过（支持增量重跑）
- 视频下载和字幕下载各自独立为单独的 Python 脚本，import.sh 只做编排
- 字幕下载失败不中断流程，提示用户手动从 downsub.com 下载

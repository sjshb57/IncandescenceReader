# 白炽阅读器 · IncandescenceReader

一个将本地 Twitter/X 存档打包成单文件便携桌面应用的离线阅读器，支持多账号。

> 此项目初衷是为 @AnIncandescence 所做的 Twitter 存档阅读器。
> 她不希望被遗忘，不想被遗忘，这或许是她最后的愿望。
> 这个项目因她而生，即使你不认识她，也请让我们悼念，愿她的来生不再痛苦，愿她会被这个世界所偏爱。
>
> 晚安，炽烈已极。

---

### 成品展示：

![](https://free.picui.cn/free/2026/05/02/69f5f0e0474e9.png)

**友链：** **[twitterarchiver.github.io/AnIncanescence](https://twitterarchiver.github.io/AnIncanescence/)**

---

### 附注

> Twitter存档组织：[TwitterArchiver](https://github.com/TwitterArchiver)已成立
> 
> 如果您想在此留档，请在[此处提交申请](https://twitterarchiver.github.io/home/guestbook.html)

---

## 项目生态

整个体系由「抓取 → 存放 → 阅读」三层构成，本仓库是阅读层里的桌面端。

```
                 Wayback Machine
                       │
                       ▼
           IncandescenceArchiver
           抓取快照 · 下载媒体 · 清洗 · 建索引
                       │
                       ▼
           TwitterArchiver 组织
           140+ 账号仓库 · GitHub Pages 托管
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
   网页阅读器      桌面阅读器        Android
twitterarchiver  Incandescence   TwitterArchiverApp
  .github.io        Reader
                  ← 本仓库
```

### 工具

| 项目 | 说明 | 技术 / 协议 |
| --- | --- | --- |
| [**TwitterArchiverApp**](https://github.com/sjshb57/TwitterArchiverApp) | Android 客户端。原生推文流、全站视图、日期树、本地书签，另有一套存档管理工具 | Kotlin · AGPL-3.0 |
| [**IncandescenceReader**](https://github.com/sjshb57/IncandescenceReader) | 本仓库。桌面离线阅读器，Electron 打包成免安装的便携应用，支持多账号 | Electron · AGPL-3.0 |
| [**IncandescenceArchiver**](https://github.com/sjshb57/IncandescenceArchiver) | 存档工具 `archive.py`，抓取快照、下载媒体、清洗 HTML，生成本阅读器所需的 `index.json` | Python · AGPL-3.0 |

### 存档

| 仓库 | 说明 |
| --- | --- |
| [**TwitterArchiver**](https://github.com/TwitterArchiver) | 存档组织，每个账号一个独立仓库，各自托管 GitHub Pages |
| [**TwitterArchiver/home**](https://github.com/TwitterArchiver/home) | 门户与聚合数据：账号清单、全站搜索索引、跨账号回复索引 |
| [**TwitterArchiver/search**](https://twitterarchiver.github.io/home/search.html) | 网页版入口，可浏览全部账号与全站搜索 |
| [**TwitterArchiver/guestbook**](https://twitterarchiver.github.io/home/guestbook.html) | 提交想要留档的账号 |

---

## 目录结构

```
IncandescenceReader/
  main.js
  package.json
  Reader.html
  icon.ico              ← 可选，替换成自己的图标
  accounts/             ← 把所有账号的数据放这里
    AnIncandescence/
      cdx_data.json     ← wayback 流程需要（导入流程不需要）
      wayback_snapshots/
        index.json      ← archive.py build-index 生成
        profile.json
        html/
        avatar/
        image/
        video/
        json/
    TauCeti_10700/      ← 多账号支持，可放任意数量
      wayback_snapshots/
        ...
```

每个账号独立存放，互不干扰。Reader 启动时自动扫 `accounts/` 下所有账号。

---

## 使用方法

### 第一步：准备数据

数据由 [**IncandescenceArchiver**](https://github.com/sjshb57/IncandescenceArchiver) 的 `archive.py` 生成，有三条来源可选。以下命令都在账号目录（`accounts/{USERNAME}/`）下执行。

**最省事的方式**：直接从 [TwitterArchiver](https://github.com/TwitterArchiver) 组织克隆现成的账号仓库，把里面的 `accounts/<账号>/wayback_snapshots/` 复制过来即可，无需跑任何脚本。

#### A. Wayback Machine（公开账号）

```bash
python ../../archive.py fetch-cdx {USERNAME}   # 抓取 CDX 快照清单
python ../../archive.py all                    # fetch-html → fetch-media → clean-html → build-index
```

#### B. 从 webarchived_tweet_downloader 导入

[webarchived_tweet_downloader](https://github.com/gfhdhytghd/webarchived_tweet_downloader) 除 Wayback 外还能走**官方 X API**，可以补到 Wayback 没存下来的推文、完整回复链和被回复的原文：

```bash
# 先用上游工具抓（在它自己的目录下）
python download_archive.py {USERNAME}

# 再回到本项目账号目录导入
python ../../archive.py convert /path/to/{USERNAME}_archive/
python ../../archive.py render-html
python ../../archive.py fetch-media
python ../../archive.py build-index
```

#### C. 从 X 官方数据导出包导入（锁推 / 私密账号）

适用于自己账号从 X 申请的完整导出包（含 `data/tweets.js`）：

```bash
python ../../archive.py import-export /path/to/twitter-{USERNAME}-export/
python ../../archive.py render-html
python ../../archive.py fetch-media
python ../../archive.py build-index
```

完整的参数说明与增量更新方式见 [IncandescenceArchiver 文档](https://github.com/sjshb57/IncandescenceArchiver)。

### 第二步：安装依赖（只需一次）

```bash
cd IncandescenceReader
npm install
```

首次安装会下载 Electron（约 100MB），需要等一会儿。

### 第三步：开发预览（可选）

```bash
npm start
```

直接打开窗口预览效果，不需要打包。

### 第四步：打包

```bash
npm run dist
```

完成后在 `dist/` 文件夹里找到：

```
dist/
  win-unpacked/
    IncandescenceReader.exe    ← 双击这个运行
    resources/
      accounts/                ← 所有账号数据
    locales/
    ...
```

**直接双击 `win-unpacked/IncandescenceReader.exe` 即可运行，无需安装，无需 Python，无需 localhost。**

### 注意事项

- `win-unpacked/` 整个文件夹就是程序本体，移动时需要整个文件夹一起移动，不能单独拷走里面的 exe
- 文件夹大小取决于存档数据量（Electron 内置 Chromium 约 150MB + 数据）
- 如果没有 `icon.ico`，打包时会用默认图标，不影响功能（可以忽略警告）
- **更新存档后不需要重新打包**，直接操作 `win-unpacked/resources/accounts/{USERNAME}/wayback_snapshots/`：
  1. 把新的 HTML 文件复制到 `.../wayback_snapshots/html/`
  2. 重新跑 `archive.py build-index` 生成新的 `index.json`
  3. 把新的 `index.json` 替换到 `.../wayback_snapshots/`
  4. 下次启动自动生效
- 添加新账号也无需重新打包：在 `resources/accounts/` 下新建账号目录放好数据即可，下次启动自动出现在切换菜单里
- 只有修改了 `Reader.html` 或 `main.js` 代码本身时，才需要重新 `npm run dist`

---

## 技术实现

### build_index.py — 索引构建

> 该脚本已合并进 [IncandescenceArchiver](https://github.com/sjshb57/IncandescenceArchiver) 的 `archive.py build-index` 子命令，本仓库保留一份独立版本便于单独使用。

扫描账号目录下 `wayback_snapshots/html/` 与 `wayback_snapshots/json/`，对每条推文从两边综合提取数据：

- **JSON 优先**：从 X API JSON 直接读取作者、时间、文本、媒体 key、引用关系等结构化字段
- **HTML 兜底**：JSON 缺失时从 HTML 解析（DateString、`#nonjsonview` 内的 `.tweet-content`）

输出 `wayback_snapshots/index.json`，每条记录包含完整字段：

```json
{
  "file": "...html",
  "timestamp": "2026-04-04T07:50:13.000Z",
  "date": "2026-04-04",
  "time": "07:50:13",
  "text": "推文正文预览...",
  "tweet_id": "...",
  "conversation_id": "...",
  "author_name": "...",
  "author_username": "@...",
  "author_avatar": "../avatar/avatar_xxx.jpg",
  "is_reply": false,
  "is_virtual": false,
  "reply_to_id": "...",
  "wanted_images": [],
  "embedded_images": [],
  "wanted_videos": [],
  "embedded_videos": []
}
```

被引用但本地无独立 HTML 的外人推文以「虚拟条目」形式加入索引（`is_virtual: true`），从 `<embedded-tweet-container>` 提取。脚本同时构建 `tweet_id_index` 来追溯祖先推文上的媒体（多层引用嵌套时正确归属图片）。

### main.js — Electron 主进程

注册自定义协议 `incr://` 处理所有资源请求，绕开 `file://` 的跨域限制，使 `Reader.html` 内的 `fetch()` 可以正常读取本地数据。

路由规则：

- `incr://local/_accounts` — 虚拟路径，运行时扫描 `accounts/` 下所有子目录的 `profile.json` 动态生成账号清单 JSON 返回
- `incr://local/accounts/{dir}/...` — 多账号数据
- `incr://local/wayback_snapshots/...` — 兼容旧的单账号目录结构
- 其他路径 — 静态资源（Reader.html 等）

使用 `registerBufferProtocol`（而非 `registerFileProtocol`），因为虚拟路径需要返回动态生成的 buffer。打包后数据目录指向 `process.resourcesPath/accounts/`，开发时指向项目根目录。

### Reader.html — 前端界面

纯原生 HTML/CSS/JS，无任何外部依赖。

**多账号切换**：启动时 fetch `incr://local/_accounts` 拿到账号清单，右上角显示切换按钮，点击弹层选账号，localStorage 记忆当前选择。切换时重设路径常量并重新加载 profile.json + index.json。

**iframe 渲染**：每条推文用独立 iframe 加载原始 HTML 存档。`onload` 时通过 `contentDocument` 直接操作 DOM 注入主题样式（明/暗两套配色）、根据 `wanted_images` / `embedded_images` 字段精准过滤媒体（避免显示破图）、折叠 embedded 引用框，最后用 `scrollHeight` 自动撑开 iframe 高度避免内部滚动条。所有这些操作完成后才标记 `dataset.loaded='1'`，作为「高度真正稳定」的信号。

**最近收录跳转**：右栏点击会切换日期 + 跳到目标推文。跳转前先 `visibility:hidden` 主列，再轮询等待目标 iframe 及其之前的 iframe 全部 `dataset.loaded='1'`（同时检查内部 `<img>` 是否 complete），主动重跑 `autoHeight` 同步高度，最后用 `getBoundingClientRect` 算位置 + `scrollTop` 直接跳转，不留滚动动画。

**搜索**：在内存中对 `index.json` 的 `text` 字段进行全文过滤，支持关键词高亮，点击结果可跳转至对应日期视图并滚动定位。所有时间戳以 UTC 存储，显示时通过 `Date` 对象转换为用户本地时区。

**引用标识**：根据 `author_username == 当前账号 username` 判断主人 vs 外人，所有非主人发的推文（无论是否虚拟条目）显示「引用」标识，正确处理 wayback 流程（外人推文均为虚拟条目）和导入流程（外人推文也有独立 HTML 存档）两种数据源。

---

## 鸣谢

感谢 @CheeseGhostfox 的启发，项目地址：<https://github.com/CheeseGhostfox/IncandescenceReader>

感谢 [@gfhdhytghd](https://github.com/gfhdhytghd) 的 [webarchived_tweet_downloader](https://github.com/gfhdhytghd/webarchived_tweet_downloader)，为本项目提供了 X API 路径的数据来源。

---

## License

Copyright © 2026 sjshb57

本项目基于 [GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.html) 开源。你可以自由使用、修改和分发本项目，但衍生作品必须同样以 AGPL-3.0 协议开源。

存档内容本身的版权归原作者所有。本项目仅做数字保存，不主张任何内容权利。

---

## 赞助

![赞助图片](https://free.picui.cn/free/2026/06/24/6a3b25866f0fd.jpg)

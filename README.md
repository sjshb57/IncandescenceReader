# 白炽阅读器 · IncandescenceReader

一个将本地 Twitter/X 存档打包成单文件便携桌面应用的离线阅读器。

> 此项目初衷是为 @AnIncandescence 用户所做的 Twitter 存档阅读器。  
> 她不希望被遗忘，不想被遗忘，这或许是她最后的愿望。  
> 这个项目因她而生，即使你不认识她，也请让我们悼念，愿她的来生不再痛苦，愿她会被这个世界所偏爱。  
>
> 晚安，炽烈已极。

## 目录结构

```
IncandescenceReader/
  main.js
  package.json
  Reader.html
  icon.ico              ← 可选，替换成自己的图标
  wayback_snapshots/    ← 把你的数据文件夹整个放进来
    index.json          ← 先用 build_index.py 生成
    profile.json
    html/
    avatar/
    image/
    video/
```

## 使用方法

### 第一步：生成索引

在 `IncandescenceReader/` 外面（也就是 `build_index.py` 所在目录）运行：

```
python build_index.py
```

生成 `wayback_snapshots/index.json`，然后把整个 `wayback_snapshots/` 文件夹放进 `IncandescenceReader/` 里。

### 第二步：安装依赖（只需一次）

```
cd IncandescenceReader
npm install
```

首次安装会下载 Electron（约 100MB），需要等一会儿。

### 第三步：开发预览（可选）

```
npm start
```

直接打开窗口预览效果，不需要打包。

### 第四步：打包成便携 exe

```
npm run dist
```

完成后在 `dist/` 文件夹里找到：

```
IncandescenceReader_portable.exe
```

**直接双击即可运行，无需安装，无需 Python，无需 localhost。**

### 注意事项

- exe 文件大小约 150~180MB（内置 Chromium），正常现象
- 如果没有 icon.ico，打包时会用默认图标，不影响功能（可以忽略警告）
- 数据文件夹 `wayback_snapshots/` 已经打包进 exe 内部，移动 exe 时不需要带着数据文件夹
- 每次更新存档（新增 HTML 文件）后，需要重新跑 `build_index.py` 然后重新 `npm run dist`

---

## 技术实现

### build_index.py — 索引构建

使用 BeautifulSoup 解析 `wayback_snapshots/html/` 下的所有 HTML 存档文件，从每个文件中提取两个核心字段：

- **时间戳**：优先从操作 `#parentdate` 元素的 `<script>` 块中提取 `dateString` 变量（即主推文的精确发布时间），若目标块缺失则降级为取文件中最后一个 `dateString`，再次失败则从文件名头部的 `YYYYMMDDHHMMSS_` 格式解析时间。
- **正文**：定位 `#nonjsonview` 容器内的第一个 `.tweet-content` 元素，先移除嵌套的 `.embedded-tweet-container`（引用推文）和所有 `<img>` 标签，再提取纯文本，截断至 500 字符。

所有记录按时间戳倒序排列后，序列化为 `index.json`，结构如下：

```json
[
  {
    "file": "20260404075013_xxxxx.html",
    "timestamp": "2026-04-04T07:50:13.000Z",
    "date": "2026-04-04",
    "time": "07:50:13",
    "text": "推文正文预览..."
  }
]
```

### main.js — Electron 主进程

注册了一个名为 `incr://` 的自定义协议，将所有资源请求映射到本地文件系统，从而绕开 `file://` 协议的跨域（CORS）限制，使 `Reader.html` 内的 `fetch()` 调用可以正常读取本地 JSON 和 HTML 文件。打包后数据目录指向 `resources/wayback_snapshots/`，开发时指向项目根目录。

`registerSchemesAsPrivileged` 在 `app.whenReady()` 之前于顶层调用，符合 Electron 的协议注册时序要求。

### Reader.html — 前端界面

纯原生 HTML/CSS/JS，无任何外部依赖。启动时通过 `fetch('incr://local/wayback_snapshots/index.json')` 加载索引，将数据按年/月/日三级结构组织为日期树，渲染在左侧边栏。

每日的帖子内容通过 `<iframe>` 加载对应的原始 HTML 存档，并在 `onload` 时通过 `contentDocument` 直接操作 iframe 内的 DOM 注入主题样式（明/暗两套配色），同时使用 `scrollHeight` 自动撑开 iframe 高度以避免内部滚动条。

搜索功能在内存中对 `index.json` 的 `text` 字段进行全文过滤，支持关键词高亮，结果点击后可跳转至对应日期视图并滚动定位到目标帖子。所有时间戳以 UTC 存储，显示时通过 `Date` 对象转换为用户本地时区。

## 鸣谢

感谢 @CheeseGhostfox 的启发，项目地址：
https://github.com/CheeseGhostfox/IncandescenceReader

---

## License

Copyright © 2026 sjshb57

本项目基于 [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html) 开源。你可以自由使用、修改和分发本项目，但衍生作品必须同样以 GPL-3.0 协议开源。
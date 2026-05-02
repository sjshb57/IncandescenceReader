# 白炽阅读器 · IncandescenceReader

一个将本地 Twitter/X 存档打包成单文件便携桌面应用的离线阅读器，支持多账号。

> 此项目初衷是为 @AnIncandescence 所做的 Twitter 存档阅读器。  
> 她不希望被遗忘，不想被遗忘，这或许是她最后的愿望。  
> 这个项目因她而生，即使你不认识她，也请让我们悼念，愿她的来生不再痛苦，愿她会被这个世界所偏爱。
>
> 晚安，炽烈已极。

---

### 成品展示：
<img src="https://free.picui.cn/free/2026/05/02/69f5f0e0474e9.png" width="100%" style="max-width: 1100px; border-radius: 8px;" />

**友链：**
**sjshb57.github.io/AnIncanescence**

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
      cdx_data.json     ← wayback 流程需要（私密账号 dump 流程不需要）
      wayback_snapshots/
        index.json      ← build_index.py 生成
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

数据有两种来源：

**A. Wayback Machine 流程（公开账号）**

依次跑 4 个脚本（在对应账号目录下，cd 进去）：

```
cd accounts/AnIncandescence
python ../../fetch_json.py     # 1. 抓 X API JSON（基于 cdx_data.json）
python ../../fetch_media.py    # 2. 基于 JSON 下载图片/视频/头像
python ../../0037.py           # 3. 下载 HTML 并改写 src 为本地路径
python ../../build_index.py    # 4. 生成 index.json 索引
```

`cdx_data.json` 需要先从 Wayback CDX API 手动下载放进去：
```
http://web.archive.org/cdx/search/cdx?url=twitter.com/{USERNAME}/status/*&output=json
```

**B. X API Dump 流程（私密账号，从导出文件转换）**

```
cd accounts/TauCeti_10700
python ../../convert_006_to_ours.py     # 1. 把 dump 转成项目格式 JSON
python ../../fetch_avatars_from_json.py # 2. 下载头像
python ../../render_html_from_json.py   # 3. 从 JSON 生成 HTML（模仿 wayback 结构）
python ../../build_index.py             # 4. 生成 index.json 索引
```

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

### 第四步：打包

```
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
    1. 把新的 HTML 文件复制到 `.../wayback_snapshots/html/`（或重新跑 render 脚本）
    2. 重新跑 `build_index.py` 生成新的 `index.json`
    3. 把新的 `index.json` 替换到 `.../wayback_snapshots/`
    4. 下次启动自动生效
- 添加新账号也无需重新打包：在 `resources/accounts/` 下新建账号目录放好数据即可，下次启动自动出现在切换菜单里
- 只有修改了 `Reader.html` 或 `main.js` 代码本身时，才需要重新 `npm run dist`

---

## 技术实现

### build_index.py — 索引构建

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
  "wanted_images": [...],
  "embedded_images": [...],
  "wanted_videos": [...],
  "embedded_videos": [...]
}
```

被引用但本地无独立 HTML 的外人推文以"虚拟条目"形式加入索引（`is_virtual: true`），从 `<embedded-tweet-container>` 提取。脚本同时构建 `tweet_id_index` 来追溯祖先推文上的媒体（多层引用嵌套时正确归属图片）。

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

**iframe 渲染**：每条推文用独立 iframe 加载原始 HTML 存档。`onload` 时通过 `contentDocument` 直接操作 DOM 注入主题样式（明/暗两套配色）、根据 `wanted_images` / `embedded_images` 字段精准过滤媒体（避免显示破图）、折叠 embedded 引用框，最后用 `scrollHeight` 自动撑开 iframe 高度避免内部滚动条。所有这些操作完成后才标记 `dataset.loaded='1'`，作为"高度真正稳定"的信号。

**最近收录跳转**：右栏点击会切换日期 + 跳到目标推文。跳转前先 `visibility:hidden` 主列，再轮询等待目标 iframe 及其之前的 iframe 全部 `dataset.loaded='1'`（同时检查内部 `<img>` 是否 complete），主动重跑 `autoHeight` 同步高度，最后用 `getBoundingClientRect` 算位置 + `scrollTop` 直接跳转，不留滚动动画。

**搜索**：在内存中对 `index.json` 的 `text` 字段进行全文过滤，支持关键词高亮，点击结果可跳转至对应日期视图并滚动定位。所有时间戳以 UTC 存储，显示时通过 `Date` 对象转换为用户本地时区。

**引用标识**：根据 `author_username == 当前账号 username` 判断主人 vs 外人，所有非主人发的推文（无论是否虚拟条目）显示"引用"标识，正确处理 wayback 流程（外人推文均为虚拟条目）和 dump 流程（外人推文也有独立 HTML 存档）两种数据源。

---

## 鸣谢

感谢 @CheeseGhostfox 的启发，项目地址：
https://github.com/CheeseGhostfox/IncandescenceReader

---

## License

Copyright © 2026 sjshb57

本项目基于 [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html) 开源。你可以自由使用、修改和分发本项目，但衍生作品必须同样以 GPL-3.0 协议开源。

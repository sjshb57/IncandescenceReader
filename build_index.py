"""
build_index.py

从 wayback_snapshots/html/ 下所有 HTML 文件提取：
  - 精确时间戳：取操作 #parentdate 的 script 块里的 dateString
    （即主推文时间，而非被引用推文的时间）
  - 正文文本：.tweet-content 的纯文本，排除引用推文部分

生成 wayback_snapshots/index.json

用法：
  python build_index.py

目录结构：
  Reader.html
  build_index.py
  build_reader.py
  wayback_snapshots/
    index.json          ← 本脚本输出
    profile.json
    html/
    avatar/
    image/
    video/
"""

import os
import re
import json
from bs4 import BeautifulSoup

# ── 配置 ──────────────────────────────────────────────────
HTML_DIR   = "./wayback_snapshots/html"
INDEX_FILE = "./wayback_snapshots/index.json"
TEXT_MAX   = 500
# ──────────────────────────────────────────────────────────


def extract_date(html_text: str) -> str:
    """
    取操作 #parentdate 的 script 块里的 dateString。

    目标结构（文件末尾）：
        <script>
        var dateString = "2026-04-04T07:50:13.000Z";
        ...
        document.querySelector("#parentdate").innerText = date;
        </script>

    策略：找所有 script 块，取同时包含 dateString 赋值
    和 #parentdate 操作的那一个。
    """
    # 用正则切出所有 <script>...</script> 块
    script_blocks = re.findall(
        r'<script[^>]*>(.*?)</script>',
        html_text, re.DOTALL | re.IGNORECASE
    )

    for block in script_blocks:
        if '#parentdate' in block or '"#parentdate"' in block or "'#parentdate'" in block:
            m = re.search(r'var\s+dateString\s*=\s*"([^"]+)"', block)
            if m:
                return m.group(1)

    # 降级：如果找不到 #parentdate 块（格式异常），
    # 取最后一个 dateString（通常主推文在最后）
    all_dates = re.findall(r'var\s+dateString\s*=\s*"([^"]+)"', html_text)
    if all_dates:
        return all_dates[-1]

    return ""


def extract_text(html_text: str) -> str:
    """
    提取主推文 .tweet-content 的纯文本。
    排除 img 标签和 embedded-tweet-container（引用推文）。
    取第一个 .tweet-content（主推文），忽略引用推文里的。
    """
    soup = BeautifulSoup(html_text, "html.parser")

    # 主推文容器是最外层 #nonjsonview 里的第一个 tweet-content
    # 先找主容器，再在里面找，避免取到引用推文的 tweet-content
    main_wrap = soup.find(id="nonjsonview") or soup.find("div", class_="tweet-container")

    container = None
    if main_wrap:
        # 跳过 embedded-tweet-container 里的内容
        for embedded in main_wrap.find_all("div", class_="embedded-tweet-container"):
            embedded.decompose()
        container = main_wrap.find("div", class_="tweet-content")

    if not container:
        # 回退：全文第一个 tweet-content
        container = soup.find("div", class_="tweet-content")

    if container:
        for img in container.find_all("img"):
            img.decompose()
        text = container.get_text(separator=" ", strip=True)
    else:
        text = soup.get_text(separator=" ", strip=True)

    text = re.sub(r"\s+", " ", text).strip()
    return text[:TEXT_MAX]


def fname_to_iso(fname: str) -> str:
    """从文件名头部 YYYYMMDDHHMMSS_ 提取 ISO 时间戳（UTC 降级用）。"""
    m = re.match(r"(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})_", fname)
    if m:
        Y, M, D, h, mi, s = m.groups()
        return f"{Y}-{M}-{D}T{h}:{mi}:{s}.000Z"
    return "1970-01-01T00:00:00.000Z"


def main():
    if not os.path.isdir(HTML_DIR):
        print(f"[错误] HTML 目录不存在：{os.path.abspath(HTML_DIR)}")
        return

    html_files = sorted(f for f in os.listdir(HTML_DIR) if f.endswith(".html"))
    total = len(html_files)
    print(f"共检测到 {total} 个 HTML 文件，开始处理...\n")

    index_data = []
    no_date    = []

    for i, fname in enumerate(html_files, 1):
        fpath = os.path.join(HTML_DIR, fname)
        with open(fpath, encoding="utf-8", errors="replace") as f:
            html_text = f.read()

        iso_date = extract_date(html_text)
        text     = extract_text(html_text)

        if not iso_date:
            no_date.append(fname)
            iso_date = fname_to_iso(fname)

        index_data.append({
            "file":      fname,
            "timestamp": iso_date,       # 完整 ISO，排序用
            "date":      iso_date[:10],  # YYYY-MM-DD，按日分组
            "time":      iso_date[11:19],# HH:MM:SS，显示用
            "text":      text,
        })

        if i % 200 == 0 or i == total:
            print(f"  进度：{i}/{total}")

    index_data.sort(key=lambda x: x["timestamp"], reverse=True)

    os.makedirs(os.path.dirname(INDEX_FILE), exist_ok=True)
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, separators=(",", ":"))

    print(f"\n完成！共 {len(index_data)} 条记录 → {os.path.abspath(INDEX_FILE)}")
    if no_date:
        print(f"警告：{len(no_date)} 个文件未找到 #parentdate，已用文件名时间戳降级：")
        for fn in no_date[:10]:
            print(f"  {fn}")
        if len(no_date) > 10:
            print(f"  … 共 {len(no_date)} 个")


if __name__ == "__main__":
    main()

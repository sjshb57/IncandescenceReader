"""
build_index.py

新增：从 HTML 提取每条推文的渲染数据，供 Reader.html 直接渲染回复卡片：
  author_name    显示名
  author_username @用户名
  author_avatar  头像相对路径（../avatar/xxx.jpg）
  body_text      正文纯文字（保留换行，去掉图片/embedded）
  images         本推文自己的图片路径列表（排除属于被引用推文的图）
"""

import os
import re
import json
from bs4 import BeautifulSoup

# ── 配置 ──────────────────────────────────────────────────────
HTML_DIR   = "./wayback_snapshots/html"
JSON_DIR   = "./wayback_snapshots/json"
INDEX_FILE = "./wayback_snapshots/index.json"
TEXT_MAX   = 500
# ──────────────────────────────────────────────────────────────


def extract_date(html_text: str) -> str:
    script_blocks = re.findall(
        r'<script[^>]*>(.*?)</script>',
        html_text, re.DOTALL | re.IGNORECASE
    )
    for block in script_blocks:
        if '#parentdate' in block or '"#parentdate"' in block or "'#parentdate'" in block:
            m = re.search(r'var\s+dateString\s*=\s*"([^"]+)"', block)
            if m:
                return m.group(1)
    all_dates = re.findall(r'var\s+dateString\s*=\s*"([^"]+)"', html_text)
    if all_dates:
        return all_dates[-1]
    return ""


def extract_render_data(html_text: str) -> dict:
    """
    从 html 文件提取渲染所需数据：
      - 主推文作者（第一个 tweet-author 块）
      - 正文文字（去掉 embedded 和图片后的纯文本，保留换行）
      - 本推文自己的图片（tweet-content 直接子级的 tweet-image，不含 embedded 内的）
      - embedded 数据（被回复/被引用推文的作者头像、用户名、文字、推文ID）
        用于生成"虚拟外人条目"，供 Reader.html 显示完整对话链
    """
    result = {
        "author_name":     "",
        "author_username": "",
        "author_avatar":   "",
        "body_text":       "",
        "images":          [],
        "embedded":        None,  # 新增：embedded 数据（如果有）
    }

    soup = BeautifulSoup(html_text, "html.parser")
    nonjson = soup.find(id="nonjsonview")
    if not nonjson:
        return result

    # 作者信息（第一个 tweet-author）
    first_author = nonjson.find("div", class_="tweet-author")
    if first_author:
        name_el  = first_author.find(class_="tweet-author-name")
        uname_el = first_author.find(class_="tweet-author-username")
        avatar_el = first_author.find("img")
        if name_el:
            result["author_name"] = name_el.get_text(strip=True)
        if uname_el:
            result["author_username"] = uname_el.get_text(strip=True)
        if avatar_el and avatar_el.get("src"):
            result["author_avatar"] = avatar_el["src"]

    # 正文内容区
    content = nonjson.find("div", class_="tweet-content")
    if not content:
        return result

    # 找 embedded-tweet-container（被引用/被回复的推文块）
    embedded = content.find("div", class_="embedded-tweet-container")

    # 提取 embedded 数据（如有）
    if embedded:
        emb_data = {
            "author_name":     "",
            "author_username": "",
            "author_avatar":   "",
            "body_text":       "",
            "tweet_id":        "",
            "timestamp":       "",  # embedded 的 script 里的 dateString
        }
        emb_author = embedded.find("div", class_="tweet-author")
        if emb_author:
            nm = emb_author.find(class_="tweet-author-name")
            un = emb_author.find(class_="tweet-author-username")
            av = emb_author.find("img")
            if nm: emb_data["author_name"]     = nm.get_text(strip=True)
            if un: emb_data["author_username"] = un.get_text(strip=True)
            if av and av.get("src"):
                emb_data["author_avatar"] = av["src"]

        # 文字（去掉 date/script）
        emb_content = embedded.find("div", class_="tweet-content")
        if emb_content:
            ec_clone = BeautifulSoup(str(emb_content), "html.parser").find("div", class_="tweet-content")
            for tag in ec_clone.find_all(["script", "img"]):
                tag.decompose()
            for p_tag in ec_clone.find_all("p", class_="date"):
                p_tag.decompose()
            for br in ec_clone.find_all("br"):
                br.replace_with("\n")
            et = ec_clone.get_text(separator="", strip=False)
            lines = [l.strip() for l in et.splitlines()]
            clean = []
            prev_empty = False
            for l in lines:
                if l == "":
                    if not prev_empty: clean.append(l)
                    prev_empty = True
                else:
                    clean.append(l); prev_empty = False
            emb_data["body_text"] = "\n".join(clean).strip()[:TEXT_MAX]

        # 从 embedded 的 <a href="..."> 提取被引用推文ID
        for a in embedded.find_all("a"):
            href = a.get("href", "")
            m = re.search(r'/status/(\d+)', href)
            if m:
                emb_data["tweet_id"] = m.group(1)
                break

        # 从 embedded 的 <script> 提取 dateString（被引用推文的时间）
        for s in embedded.find_all("script"):
            mt = re.search(r'var\s+dateString\s*=\s*"([^"]+)"', s.string or "")
            if mt:
                emb_data["timestamp"] = mt.group(1)
                break

        result["embedded"] = emb_data

    # 提取图片：只要不在 embedded 内部的 tweet-image
    for img in content.find_all("img", class_="tweet-image"):
        in_embedded = False
        if embedded:
            p = img.parent
            while p:
                if p == embedded:
                    in_embedded = True
                    break
                p = p.parent
        if not in_embedded:
            src = img.get("src", "")
            if src:
                result["images"].append(src)

    # 提取纯文字（移除 embedded 和所有 img）
    content_clone = BeautifulSoup(str(content), "html.parser").find("div", class_="tweet-content")
    emb_clone = content_clone.find("div", class_="embedded-tweet-container")
    if emb_clone:
        emb_clone.decompose()
    for img in content_clone.find_all("img"):
        img.decompose()
    for script in content_clone.find_all("script"):
        script.decompose()
    for p_tag in content_clone.find_all("p", class_="date"):
        p_tag.decompose()

    for br in content_clone.find_all("br"):
        br.replace_with("\n")

    body = content_clone.get_text(separator="", strip=False)
    lines = [l.strip() for l in body.splitlines()]
    clean_lines = []
    prev_empty = False
    for l in lines:
        if l == "":
            if not prev_empty:
                clean_lines.append(l)
            prev_empty = True
        else:
            clean_lines.append(l)
            prev_empty = False
    body = "\n".join(clean_lines).strip()
    result["body_text"] = body[:TEXT_MAX]

    return result


def extract_text(html_text: str) -> str:
    """搜索用纯文本（原有逻辑保留）"""
    soup = BeautifulSoup(html_text, "html.parser")
    main_wrap = soup.find(id="nonjsonview") or soup.find("div", class_="tweet-container")
    container = None
    if main_wrap:
        for embedded in main_wrap.find_all("div", class_="embedded-tweet-container"):
            embedded.decompose()
        container = main_wrap.find("div", class_="tweet-content")
    if not container:
        container = soup.find("div", class_="tweet-content")
    if container:
        for img in container.find_all("img"):
            img.decompose()
        text = container.get_text(separator=" ", strip=True)
    else:
        text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:TEXT_MAX]


def extract_tweet_id_from_filename(fname: str) -> str:
    m = re.search(r'status_(\d+)', fname)
    return m.group(1) if m else ""


def fname_to_iso(fname: str) -> str:
    m = re.match(r"(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})_", fname)
    if m:
        Y, M, D, h, mi, s = m.groups()
        return f"{Y}-{M}-{D}T{h}:{mi}:{s}.000Z"
    return "1970-01-01T00:00:00.000Z"


def extract_from_json(json_data: dict) -> dict:
    result = {
        "tweet_id":        "",
        "conversation_id": "",
        "is_reply":        False,
        "reply_to_id":     "",
        "reply_type":      "",
        "has_quoted":      False,
        "quoted_id":       "",
        "has_media":       False,
        "media_keys":      [],
    }
    data     = json_data.get("data", {})
    includes = json_data.get("includes", {})
    result["tweet_id"]        = str(data.get("id", ""))
    result["conversation_id"] = str(data.get("conversation_id", ""))
    for ref in data.get("referenced_tweets", []):
        rtype, rid = ref.get("type", ""), str(ref.get("id", ""))
        if rtype == "replied_to":
            result["is_reply"]    = True
            result["reply_to_id"] = rid
            result["reply_type"]  = "replied_to"
        elif rtype == "quoted":
            result["has_quoted"]  = True
            result["quoted_id"]   = rid
            result["reply_type"]  = "quoted"
    att = data.get("attachments", {})
    mk  = att.get("media_keys", [])
    result["media_keys"] = mk
    result["has_media"]  = len(mk) > 0 or bool(includes.get("media"))
    return result


def extract_from_html_fallback(html_text: str, fname: str) -> dict:
    result = {
        "tweet_id":        extract_tweet_id_from_filename(fname),
        "conversation_id": "",
        "is_reply":        False,
        "reply_to_id":     "",
        "reply_type":      "",
        "has_quoted":      False,
        "quoted_id":       "",
        "has_media":       False,
        "media_keys":      [],
    }
    soup = BeautifulSoup(html_text, "html.parser")
    nonjson = soup.find(id="nonjsonview")
    if not nonjson:
        return result
    imgs = nonjson.find_all("img", class_="tweet-image")
    result["has_media"] = len(imgs) > 0
    embedded = nonjson.find("div", class_="embedded-tweet-container")
    if embedded:
        for a in embedded.find_all("a"):
            href = a.get("href", "")
            m = re.search(r'/status/(\d+)', href)
            if m:
                ref_id   = m.group(1)
                user_m   = re.search(r'twitter\.com/([^/]+)/status', href)
                ref_user = user_m.group(1) if user_m else ""
                own_uname = ""
                uname_div = nonjson.find(class_="tweet-author-username")
                if uname_div:
                    own_uname = uname_div.get_text(strip=True).lstrip("@")
                if ref_user.lower() == own_uname.lower():
                    result["has_quoted"]  = True
                    result["quoted_id"]   = ref_id
                    result["reply_type"]  = "quoted_self"
                else:
                    result["has_quoted"]  = True
                    result["quoted_id"]   = ref_id
                    result["reply_type"]  = "quoted"
                break
    return result


def main():
    if not os.path.isdir(HTML_DIR):
        print(f"[错误] HTML 目录不存在：{os.path.abspath(HTML_DIR)}")
        return

    html_files = sorted(f for f in os.listdir(HTML_DIR) if f.endswith(".html"))
    total = len(html_files)
    print(f"共检测到 {total} 个 HTML 文件")

    json_dir_exists = os.path.isdir(JSON_DIR)
    json_count = len([f for f in os.listdir(JSON_DIR) if f.endswith(".json")]) if json_dir_exists else 0
    print(f"JSON 目录：{'存在' if json_dir_exists else '不存在'}，已有 {json_count} 个 JSON 文件\n")

    index_data = []
    no_date    = []
    no_json    = []
    # 收集所有 embedded 中的外人推文数据，作为虚拟条目（仅当本地没有同ID的真实条目时加入）
    # key: tweet_id, value: virtual record dict
    virtual_entries = {}

    for i, fname in enumerate(html_files, 1):
        fpath = os.path.join(HTML_DIR, fname)
        with open(fpath, encoding="utf-8", errors="replace") as f:
            html_text = f.read()

        iso_date    = extract_date(html_text)
        text        = extract_text(html_text)
        render_data = extract_render_data(html_text)

        if not iso_date:
            no_date.append(fname)
            iso_date = fname_to_iso(fname)

        json_fname = os.path.splitext(fname)[0] + ".json"
        json_path  = os.path.join(JSON_DIR, json_fname)

        if os.path.exists(json_path):
            with open(json_path, encoding="utf-8") as jf:
                json_data = json.load(jf)
            meta = extract_from_json(json_data)
        else:
            no_json.append(fname)
            meta = extract_from_html_fallback(html_text, fname)

        record = {
            "file":            fname,
            "timestamp":       iso_date,
            "date":            iso_date[:10],
            "time":            iso_date[11:19],
            "text":            text,
            # 关系字段
            "tweet_id":        meta["tweet_id"],
            "conversation_id": meta["conversation_id"],
            "is_reply":        meta["is_reply"],
            "reply_to_id":     meta["reply_to_id"],
            "reply_type":      meta["reply_type"],
            "has_quoted":      meta["has_quoted"],
            "quoted_id":       meta["quoted_id"],
            "has_media":       meta["has_media"],
            "media_keys":      meta["media_keys"],
            # 渲染字段（供 Reader.html 直接渲染回复卡片，无需 iframe）
            "author_name":     render_data["author_name"],
            "author_username": render_data["author_username"],
            "author_avatar":   render_data["author_avatar"],
            "body_text":       render_data["body_text"],
            # 图片：如果 media_keys 为空，说明本推文无媒体，
            # 爬虫从被引用推文复制来的图片不属于本推文，过滤掉
            "images":          render_data["images"] if meta.get("media_keys") else [],
            "is_virtual":      False,
        }
        index_data.append(record)

        # 收集 embedded 里的外人推文数据作为虚拟条目
        emb = render_data.get("embedded")
        if emb and emb.get("tweet_id"):
            vid = emb["tweet_id"]
            # 只在尚未收集过这个 ID 时才加入（避免重复）
            if vid not in virtual_entries:
                ts = emb.get("timestamp") or ""
                virtual_entries[vid] = {
                    "file":            "",  # 虚拟条目无对应 html 文件
                    "timestamp":       ts,
                    "date":            ts[:10],
                    "time":            ts[11:19],
                    "text":            emb.get("body_text", "")[:TEXT_MAX],
                    "tweet_id":        vid,
                    "conversation_id": "",
                    "is_reply":        False,
                    "reply_to_id":     "",
                    "reply_type":      "",
                    "has_quoted":      False,
                    "quoted_id":       "",
                    "has_media":       False,
                    "media_keys":      [],
                    "author_name":     emb.get("author_name", ""),
                    "author_username": emb.get("author_username", ""),
                    "author_avatar":   emb.get("author_avatar", ""),
                    "body_text":       emb.get("body_text", ""),
                    "images":          [],
                    "is_virtual":      True,
                }

        if i % 200 == 0 or i == total:
            print(f"  进度：{i}/{total}（json覆盖：{i - len(no_json)}/{i}）")

    # 只保留本地没有真实条目的虚拟条目（避免和本地推文重复）
    real_ids = {r["tweet_id"] for r in index_data if r.get("tweet_id")}
    added_virtual = 0
    for vid, vrec in virtual_entries.items():
        if vid not in real_ids:
            index_data.append(vrec)
            added_virtual += 1

    index_data.sort(key=lambda x: x["timestamp"], reverse=True)

    os.makedirs(os.path.dirname(INDEX_FILE), exist_ok=True)
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, separators=(",", ":"))

    print(f"\n完成！共 {len(index_data)} 条记录 → {os.path.abspath(INDEX_FILE)}")
    print(f"  其中 {added_virtual} 条为虚拟条目（从 embedded-tweet-container 提取的外人推文，本地无独立 html 文件）")
    if no_date:
        print(f"\n警告：{len(no_date)} 个文件未找到 #parentdate，已用文件名时间戳降级")
    if no_json:
        pct = len(no_json) / total * 100
        print(f"\n注意：{len(no_json)} 个文件（{pct:.1f}%）无对应 JSON，使用 HTML 结构降级推断")
        print("  → 运行 fetch_json.py 补全 JSON 数据后，重新运行本脚本可获得完整字段")


if __name__ == "__main__":
    main()

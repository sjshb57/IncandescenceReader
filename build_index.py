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
IMAGE_DIR  = "./wayback_snapshots/image"
VIDEO_DIR  = "./wayback_snapshots/video"
INDEX_FILE = "./wayback_snapshots/index.json"
TEXT_MAX   = 500
# ──────────────────────────────────────────────────────────────


def build_image_index() -> dict:
    """
    扫描 image/ 目录，建立 basename → 相对路径的映射。
    basename 是 Twitter 媒体文件的核心 ID（如 G7F7hTpaIAEw53d 或 HFJ8JQ5aAAAXUq_）。
    本地文件名格式：
      - {timestamp}_..._media_BASENAME_jpg.jpg  (URL末尾.jpg 被 safe_filename 转成 _jpg 然后再加扩展名)
      - {timestamp}_..._media_BASENAME.jpg      (因 clean[:100] 截断后没有 _jpg 后缀的情况)
    注意：BASENAME 可以包含下划线（Twitter 媒体ID会用下划线作填充）
    返回 {basename: "../image/完整文件名.jpg", ...}
    """
    if not os.path.isdir(IMAGE_DIR):
        return {}
    index = {}
    # 优先索引新命名（_pbs_twimg_com_ 是 fetch_media.py 从原站直链下载的干净文件）
    fnames = sorted(
        os.listdir(IMAGE_DIR),
        key=lambda f: (0 if "_pbs_twimg_com_" in f else 1, f)
    )
    for fname in fnames:
        m = re.search(r'_media_(.+?)_(?:jpg|png|gif|webp|jpeg)\.(?:jpg|png|gif|webp|jpeg)$', fname, re.IGNORECASE)
        if not m:
            m = re.search(r'_media_(.+?)\.(?:jpg|png|gif|webp|jpeg)$', fname, re.IGNORECASE)
        if m:
            basename = m.group(1)
            if basename not in index:
                index[basename] = f"../image/{fname}"
    return index


def build_video_index() -> dict:
    """
    扫描 video/ 目录，建立 media_key(数字部分) → 相对路径的映射。
    本地文件名形如：
      - {timestamp}_..._amplify_video_2040869759278080000_..._mp4.mp4
      - {timestamp}_..._ext_tw_video_1911056663718567937_..._mp4.mp4
    返回 {media_key_number: "../video/完整文件名.mp4", ...}
    """
    if not os.path.isdir(VIDEO_DIR):
        return {}
    index = {}
    fnames = sorted(
        os.listdir(VIDEO_DIR),
        key=lambda f: (0 if "_video_twimg_com_" in f else 1, f)
    )
    for fname in fnames:
        m = re.search(r'(?:amplify_video|ext_tw_video|tweet_video)[/_](\d+)', fname)
        if m:
            key = m.group(1)
            if key not in index:
                index[key] = f"../video/{fname}"
    return index


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


def build_tweet_id_index() -> dict:
    """
    扫描 json/ 目录，建立 tweet_id → json 文件路径 的映射。
    用于沿 referenced_tweets 链向上追溯祖先推文（找祖先的媒体）。

    一条推文的 tweet_id = json 文件里 data.id。
    通常 tweet_id 也在文件名末尾（如 ..._status_2030324107624272034.json），
    但用 data.id 作权威来源更稳。
    """
    if not os.path.isdir(JSON_DIR):
        return {}
    index = {}
    for fname in os.listdir(JSON_DIR):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(JSON_DIR, fname)
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
            tid = str(data.get("data", {}).get("id", ""))
            if tid and tid not in index:
                index[tid] = fpath
        except Exception:
            continue
    return index


def _media_lookup_for_json(json_data: dict):
    """
    从一份 json 提取 media_key → image_basename / video_key 映射。
    返回 (mk_to_image_basename, mk_to_video_key)。
    供祖先链遍历时复用。
    """
    mk_to_image_basename = {}
    mk_to_video_key      = {}
    includes = json_data.get("includes", {}) or {}
    for media in includes.get("media", []) or []:
        mkey  = media.get("media_key", "")
        mtype = media.get("type", "")
        if mtype == "photo":
            url = media.get("url", "") or media.get("preview_image_url", "")
            if url:
                m = re.search(r'/media/([^/?#]+?)\.(?:jpg|png|gif|webp|jpeg)(?:[?#]|$)', url, re.IGNORECASE)
                if m:
                    mk_to_image_basename[mkey] = m.group(1)
        elif mtype in ("video", "animated_gif"):
            key = None
            for v in media.get("variants", []) or []:
                if v.get("content_type") == "video/mp4":
                    url = v.get("url", "")
                    m = re.search(r'(?:amplify_video|ext_tw_video|tweet_video)[/_](\d+)', url)
                    if m:
                        key = m.group(1)
                        break
            if not key:
                m = re.search(r'(\d+)$', mkey)
                if m:
                    key = m.group(1)
            if key:
                mk_to_video_key[mkey] = key
    return mk_to_image_basename, mk_to_video_key


def collect_ancestor_media(start_tweet_id: str,
                           tweet_id_index: dict,
                           max_depth: int = 50) -> tuple:
    """
    从 start_tweet_id 出发，沿 referenced_tweets 链向上追溯，
    收集所有祖先推文的图/视频。

    断链停止：某层祖先没有对应本地 json 时，整条链向上的追溯就停止。

    返回 (image_basenames, video_keys)，按"从直接被引用 → 越远祖先"的顺序。
    用 visited 防环（虽然推文链不应有环，保险起见）。
    """
    image_basenames = []
    video_keys      = []
    visited = set()
    current_id = start_tweet_id
    depth = 0

    while current_id and current_id not in visited and depth < max_depth:
        visited.add(current_id)
        depth += 1
        json_path = tweet_id_index.get(current_id)
        if not json_path:
            break  # 断链，停止
        try:
            with open(json_path, encoding="utf-8") as f:
                ancestor_data = json.load(f)
        except Exception:
            break

        # 提取该祖先的 media
        mk_img, mk_vid = _media_lookup_for_json(ancestor_data)
        anc_main = ancestor_data.get("data", {}) or {}
        anc_mk = (anc_main.get("attachments", {}) or {}).get("media_keys", []) or []
        for k in anc_mk:
            if k in mk_img:
                image_basenames.append(mk_img[k])
            if k in mk_vid:
                video_keys.append(mk_vid[k])

        # 向上一层：找它的 referenced_tweets 里的 replied_to 或 quoted
        next_id = None
        for ref in (anc_main.get("referenced_tweets") or []):
            if ref.get("type") in ("replied_to", "quoted"):
                next_id = str(ref.get("id", ""))
                break
        current_id = next_id

    return image_basenames, video_keys


def extract_from_json(json_data: dict, tweet_id_index: dict = None) -> dict:
    result = {
        "tweet_id":                "",
        "conversation_id":         "",
        "is_reply":                False,
        "reply_to_id":             "",
        "reply_type":              "",
        "has_quoted":              False,
        "quoted_id":               "",
        "has_media":               False,
        "media_keys":              [],
        "wanted_basenames":        [],   # 主推文应显示的图 basename 列表
        "embedded_basenames":      [],   # embedded 应显示的图 basename 列表
        "wanted_video_keys":       [],   # 主推文应显示的视频 key 列表（数字 media_key）
        "embedded_video_keys":     [],   # embedded 应显示的视频 key 列表
        "remove_urls":             [],   # 主推文文字里要删除的 t.co 短链（图片/引用占位）
        "embedded_remove_urls":    [],   # embedded 文字里要删除的 t.co 短链
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

    # 建立 media_key → 图 basename / 视频 key 的映射
    # 图 URL 形如 https://pbs.twimg.com/media/G7F7hTpaIAEw53d.jpg → basename = G7F7hTpaIAEw53d
    # 视频 URL 形如 https://video.twimg.com/amplify_video/2040869759278080000/vid/avc1/...mp4 → key = 2040869759278080000
    mk_to_image_basename = {}  # media_key → 图的 basename
    mk_to_video_key      = {}  # media_key → 视频 key（数字）
    for media in includes.get("media", []):
        mkey  = media.get("media_key", "")
        mtype = media.get("type", "")
        if mtype == "photo":
            url = media.get("url", "") or media.get("preview_image_url", "")
            if url:
                m = re.search(r'/media/([^/?#]+?)\.(?:jpg|png|gif|webp|jpeg)(?:[?#]|$)', url, re.IGNORECASE)
                if m:
                    mk_to_image_basename[mkey] = m.group(1)
        elif mtype in ("video", "animated_gif"):
            # 视频 key 从 variants 的 URL 提取，兜底用 media_key 里的数字部分
            key = None
            for v in media.get("variants", []) or []:
                if v.get("content_type") == "video/mp4":
                    url = v.get("url", "")
                    m = re.search(r'(?:amplify_video|ext_tw_video|tweet_video)[/_](\d+)', url)
                    if m:
                        key = m.group(1)
                        break
            if not key:
                m = re.search(r'(\d+)$', mkey)
                if m:
                    key = m.group(1)
            if key:
                mk_to_video_key[mkey] = key

    # 主推文应显示的图/视频
    result["wanted_basenames"]  = [mk_to_image_basename[k] for k in mk if k in mk_to_image_basename]
    result["wanted_video_keys"] = [mk_to_video_key[k]      for k in mk if k in mk_to_video_key]

    # embedded 应显示的图/视频：referenced_tweets 对应推文的 media_keys
    ref_ids = [str(r.get("id", "")) for r in data.get("referenced_tweets", [])]
    for t in includes.get("tweets", []):
        if str(t.get("id", "")) in ref_ids:
            t_mk = t.get("attachments", {}).get("media_keys", [])
            for k in t_mk:
                if k in mk_to_image_basename:
                    result["embedded_basenames"].append(mk_to_image_basename[k])
                if k in mk_to_video_key:
                    result["embedded_video_keys"].append(mk_to_video_key[k])

    # 祖先链：沿 referenced_tweets 向上递归追溯所有祖先推文的图/视频
    # 例：A reply→B reply→C，C 的 embedded 应显示 B 的图（直接被引用），
    # 但如果 B 没图、B 又 reply 了 A，那 A 的图也要纳入。
    # 数据源是本地 json/，断链停止。
    #
    # 第一层祖先（直接被引用）的图已经在上面 includes.tweets 处理过了，
    # 这里要追溯第2层及以上。优先从 includes.tweets 里拿第1层祖先的 referenced_tweets
    # 信息（这样即使第1层祖先没有独立 json 也能拿到祖父ID），然后用 tweet_id_index 追溯。
    if tweet_id_index:
        seen_imgs = set(result["embedded_basenames"])
        seen_vids = set(result["embedded_video_keys"])
        # 用 includes.tweets 索引快速找到任意 ref_id 对应的推文数据（含 referenced_tweets）
        included_by_id = {str(t.get("id", "")): t for t in includes.get("tweets", [])}
        for first_ancestor_id in ref_ids:
            # 取第1层祖先的 referenced_tweets（祖父）
            grand_ids = []
            anc_in_includes = included_by_id.get(first_ancestor_id)
            if anc_in_includes:
                # 优先从 includes.tweets 拿（不依赖独立 json 文件）
                for ref in (anc_in_includes.get("referenced_tweets") or []):
                    if ref.get("type") in ("replied_to", "quoted"):
                        grand_ids.append(str(ref.get("id", "")))
            else:
                # includes.tweets 没收录这条祖先 → 尝试从本地独立 json 拿
                anc_path = tweet_id_index.get(first_ancestor_id)
                if anc_path:
                    try:
                        with open(anc_path, encoding="utf-8") as f:
                            anc_data = json.load(f)
                        for ref in (anc_data.get("data", {}).get("referenced_tweets") or []):
                            if ref.get("type") in ("replied_to", "quoted"):
                                grand_ids.append(str(ref.get("id", "")))
                    except Exception:
                        pass
            # 从每个祖父开始追溯（递归，沿祖先链向上）
            for grand_id in grand_ids:
                a_imgs, a_vids = collect_ancestor_media(grand_id, tweet_id_index)
                for b in a_imgs:
                    if b not in seen_imgs:
                        seen_imgs.add(b)
                        result["embedded_basenames"].append(b)
                for v in a_vids:
                    if v not in seen_vids:
                        seen_vids.add(v)
                        result["embedded_video_keys"].append(v)

    # 主推文的冗余短链（要从文字里删除）：
    #   - media_key 非空：图片/视频短链（图已直接显示，短链多余）
    #   - expanded_url 含 /status/：引用预览短链（embedded 已显示）
    # 普通分享链接（如网易云、网页）保留
    seen_urls = set()
    for u in data.get("entities", {}).get("urls", []):
        url = u.get("url", "")
        if not url or url in seen_urls:
            continue
        is_media = bool(u.get("media_key"))
        is_status = '/status/' in u.get("expanded_url", "")
        if is_media or is_status:
            result["remove_urls"].append(url)
            seen_urls.add(url)

    # embedded 推文的冗余短链
    seen_urls2 = set()
    for t in includes.get("tweets", []):
        if str(t.get("id", "")) not in ref_ids:
            continue
        for u in t.get("entities", {}).get("urls", []):
            url = u.get("url", "")
            if not url or url in seen_urls2:
                continue
            is_media = bool(u.get("media_key"))
            is_status = '/status/' in u.get("expanded_url", "")
            if is_media or is_status:
                result["embedded_remove_urls"].append(url)
                seen_urls2.add(url)

    return result


def extract_from_html_fallback(html_text: str, fname: str) -> dict:
    result = {
        "tweet_id":                extract_tweet_id_from_filename(fname),
        "conversation_id":         "",
        "is_reply":                False,
        "reply_to_id":             "",
        "reply_type":              "",
        "has_quoted":              False,
        "quoted_id":               "",
        "has_media":               False,
        "media_keys":              [],
        "wanted_basenames":        [],
        "embedded_basenames":      [],
        "wanted_video_keys":       [],
        "embedded_video_keys":     [],
        "remove_urls":             [],
        "embedded_remove_urls":[],
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
    print(f"JSON 目录：{'存在' if json_dir_exists else '不存在'}，已有 {json_count} 个 JSON 文件")

    # 建立本地图片索引：basename → 相对路径
    image_index = build_image_index()
    video_index = build_video_index()
    print(f"本地图片索引：{len(image_index)} 张图片（按 basename 索引）")
    print(f"本地视频索引：{len(video_index)} 个视频（按 media_key 索引）")
    # 建立 tweet_id → json 文件路径 映射，用于祖先链追溯
    tweet_id_index = build_tweet_id_index()
    print(f"本地推文索引：{len(tweet_id_index)} 条 tweet_id（用于祖先链追溯）\n")

    index_data = []
    no_date    = []
    no_json    = []
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
            meta = extract_from_json(json_data, tweet_id_index)
        else:
            no_json.append(fname)
            meta = extract_from_html_fallback(html_text, fname)

        # 把 basename / media_key 转换成实际本地相对路径
        wanted_images    = [image_index[b] for b in meta.get("wanted_basenames",    []) if b in image_index]
        embedded_images  = [image_index[b] for b in meta.get("embedded_basenames",  []) if b in image_index]
        wanted_videos    = [video_index[k] for k in meta.get("wanted_video_keys",   []) if k in video_index]
        embedded_videos  = [video_index[k] for k in meta.get("embedded_video_keys", []) if k in video_index]

        # 清理 body_text 和 text 里的冗余短链（用于回复卡片直接展示）
        # 用 meta["remove_urls"] 删除冗余短链，整理空格
        def clean_urls(s, urls):
            if not s or not urls:
                return s
            for u in urls:
                s = s.replace(u, "")
            # 整理空格：多个空格→1个，行尾空格删除，行首空格删除
            s = re.sub(r'[ \t]{2,}', ' ', s)
            s = re.sub(r'[ \t]+\n', '\n', s)
            s = re.sub(r'\n[ \t]+', '\n', s)
            return s.strip()

        clean_body = clean_urls(render_data["body_text"], meta.get("remove_urls", []))
        clean_text = clean_urls(text, meta.get("remove_urls", []))

        record = {
            "file":            fname,
            "timestamp":       iso_date,
            "date":            iso_date[:10],
            "time":            iso_date[11:19],
            "text":            clean_text,
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
            # 渲染字段
            "author_name":     render_data["author_name"],
            "author_username": render_data["author_username"],
            "author_avatar":   render_data["author_avatar"],
            "body_text":       clean_body,
            # images：本推文（卡片渲染用，回复tab的展开卡片）的图列表
            "images":          render_data["images"] if meta.get("media_keys") else [],
            # Reader.html 注入到 iframe 用：
            #   - wanted_*：本推文外层应该显示的媒体（其他要隐藏，避免被引用推文的媒体错位显示）
            #   - embedded_*：embedded 里应该插入的媒体（解决 embedded 只有短链没图/视频的问题）
            "wanted_images":     wanted_images,
            "embedded_images":   embedded_images,
            "wanted_videos":     wanted_videos,
            "embedded_videos":   embedded_videos,
            # 冗余短链：本推文/embedded 文字里要删除的 t.co 短链（图片占位+引用占位，不删普通分享链接）
            # Reader.html 用于清理 iframe 内的文字（卡片渲染用的 body_text 已在上面清理过）
            "remove_urls":         meta.get("remove_urls", []),
            "embedded_remove_urls":meta.get("embedded_remove_urls", []),
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
                # 清理虚拟条目里的冗余短链
                emb_body = clean_urls(emb.get("body_text", ""), meta.get("embedded_remove_urls", []))[:TEXT_MAX]
                virtual_entries[vid] = {
                    "file":            "",  # 虚拟条目无对应 html 文件
                    "timestamp":       ts,
                    "date":            ts[:10],
                    "time":            ts[11:19],
                    "text":            emb_body,
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
                    "body_text":       emb_body,
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

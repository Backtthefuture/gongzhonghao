#!/usr/bin/env python3
"""公众号草稿箱发布脚本。

将 wechat-formatter 生成的 HTML 文章发布到微信公众号草稿箱。
自动处理：base64 图片上传到 ImgBB -> HTML 瘦身 -> 调用发布 API。

用法：
    python3 publish_to_wechat.py \
        --html outputs/wechat/article.html \
        --cover /tmp/cover_main.png \
        --title "文章标题" \
        --summary "文章摘要" \
        [--appid wxXXXXXXXX] \
        [--config config.yaml]
"""

import sys
import os
import re
import json
import base64
import ssl
import time
import argparse
import urllib.request
import urllib.parse

# Create SSL context that doesn't verify certificates (for expired certs)
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))

from upload_imgbb import upload_to_imgbb, load_imgbb_key


def load_wechat_config(config_path=None):
    """从 config.yaml 读取微信 API 配置。"""
    config_path = config_path or os.path.join(SKILL_DIR, "config.yaml")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config not found: {config_path}")
    with open(config_path, "r") as f:
        content = f.read()

    config = {}
    lines = content.split("\n")
    current_section = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue
        if not line.startswith(" ") and stripped.endswith(":"):
            current_section = stripped[:-1]
            continue
        if ":" in stripped:
            key, val = stripped.split(":", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if current_section:
                config[f"{current_section}.{key}"] = val
            else:
                config[key] = val

    return {
        "base_url": config.get("wechat_api.base_url", ""),
        "api_key": config.get("wechat_api.api_key", ""),
        "imgbb_key": config.get("imgbb.api_key", ""),
    }


def get_wechat_appid(base_url, api_key):
    """调用 /wechat-accounts 获取第一个公众号的 appid。"""
    print("[1/4] Fetching WeChat account info...")
    req = urllib.request.Request(
        f"{base_url}/wechat-accounts",
        data=json.dumps({}).encode("utf-8"),
        method="POST",
        headers={
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        },
    )
    resp = urllib.request.urlopen(req, timeout=30, context=_ssl_ctx)
    result = json.loads(resp.read())
    if not result.get("success"):
        raise RuntimeError(f"Failed to get accounts: {result}")
    accounts = result["data"]["accounts"]
    if not accounts:
        raise RuntimeError("No WeChat accounts found")
    appid = accounts[0]["wechatAppid"]
    name = accounts[0].get("name", "unknown")
    print(f"  Found account: {name} ({appid})")
    return appid


def upload_html_images(html_content, slug, imgbb_key):
    """扫描 HTML 中的 base64 图片，上传到 ImgBB，返回替换后的 HTML。"""
    print("[2/4] Uploading article images to ImgBB...")

    pattern = r'src="(data:image/(?:png|jpeg|jpg|gif|webp);base64,([A-Za-z0-9+/=]+))"'
    matches = list(re.finditer(pattern, html_content))

    if not matches:
        print("  No base64 images found, skipping upload")
        return html_content

    print(f"  Found {len(matches)} base64 images to upload")

    for i, match in enumerate(matches):
        full_src = match.group(1)
        b64_data = match.group(2)
        name = f"{slug}_img{i+1}"

        tmp_path = f"/tmp/imgbb_upload_{i}.png"
        with open(tmp_path, "wb") as f:
            f.write(base64.b64decode(b64_data))

        try:
            url = upload_to_imgbb(tmp_path, name, api_key=imgbb_key)
            html_content = html_content.replace(
                f'src="{full_src}"',
                f'src="{url}"',
                1,
            )
            size_kb = len(b64_data) * 3 / 4 / 1024
            print(f"  [{i+1}/{len(matches)}] Uploaded ({size_kb:.0f}KB) -> {url}")
        except Exception as e:
            print(f"  [{i+1}/{len(matches)}] FAILED: {e}", file=sys.stderr)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    return html_content


def extract_body(html_content):
    """提取 <body> 内容，去掉 html/head/body 标签壳。"""
    body_match = re.search(r"<body[^>]*>(.*)</body>", html_content, re.DOTALL)
    return body_match.group(1).strip() if body_match else html_content


def upload_cover(cover_path, slug, imgbb_key):
    """上传封面图到 ImgBB。"""
    print("[3/4] Uploading cover image to ImgBB...")
    url = upload_to_imgbb(cover_path, f"{slug}_cover", api_key=imgbb_key)
    print(f"  Cover uploaded -> {url}")
    return url


def publish_to_draft(base_url, api_key, appid, title, summary, content, cover_url):
    """调用 wechat-publish API 发布到草稿箱。"""
    print("[4/4] Publishing to WeChat draft box...")

    payload = {
        "wechatAppid": appid,
        "title": title[:64],
        "content": content,
        "summary": summary[:120],
        "coverImage": cover_url,
        "contentFormat": "html",
        "articleType": "news",
    }

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    content_size = len(data) / 1024
    print(f"  Payload size: {content_size:.1f}KB")

    req = urllib.request.Request(
        f"{base_url}/wechat-publish",
        data=data,
        method="POST",
        headers={
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        },
    )

    resp = urllib.request.urlopen(req, timeout=120, context=_ssl_ctx)
    result = json.loads(resp.read())
    return result


def main():
    parser = argparse.ArgumentParser(description="Publish article to WeChat draft box")
    parser.add_argument("--html", required=True, help="WeChat HTML file path")
    parser.add_argument("--cover", required=True, help="Cover image PNG path")
    parser.add_argument("--title", required=True, help="Article title (max 64 chars)")
    parser.add_argument("--summary", required=True, help="Article summary (max 120 chars)")
    parser.add_argument("--appid", default=None, help="WeChat appid (auto-detect if omitted)")
    parser.add_argument("--slug", default="article", help="Slug for naming uploaded images")
    parser.add_argument("--config", default=None, help="Config YAML path")
    args = parser.parse_args()

    config = load_wechat_config(args.config)
    if not config["base_url"] or not config["api_key"]:
        print("ERROR: wechat_api.base_url and wechat_api.api_key required in config.yaml",
              file=sys.stderr)
        sys.exit(1)
    if not config["imgbb_key"]:
        print("ERROR: imgbb.api_key required in config.yaml", file=sys.stderr)
        sys.exit(1)

    with open(args.html, "r", encoding="utf-8") as f:
        html_content = f.read()

    original_size = len(html_content) / 1024
    print(f"Original HTML size: {original_size:.1f}KB")

    appid = args.appid
    if not appid:
        appid = get_wechat_appid(config["base_url"], config["api_key"])

    html_content = upload_html_images(html_content, args.slug, config["imgbb_key"])

    body_content = extract_body(html_content)
    slim_size = len(body_content) / 1024
    print(f"  Slimmed HTML: {original_size:.1f}KB -> {slim_size:.1f}KB "
          f"({(1 - slim_size/original_size)*100:.1f}% reduction)")

    cover_url = upload_cover(args.cover, args.slug, config["imgbb_key"])

    result = publish_to_draft(
        config["base_url"],
        config["api_key"],
        appid,
        args.title,
        args.summary,
        body_content,
        cover_url,
    )

    print("\n" + "=" * 50)
    if result.get("success"):
        pub_data = result.get("data", {})
        print("SUCCESS! Article published to draft box.")
        print(f"  publicationId: {pub_data.get('publicationId', 'N/A')}")
        print(f"  mediaId: {pub_data.get('mediaId', 'N/A')}")
        print(f"  status: {pub_data.get('status', 'N/A')}")
    else:
        print("FAILED to publish.", file=sys.stderr)
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(1)

    print("\n__JSON_RESULT__")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

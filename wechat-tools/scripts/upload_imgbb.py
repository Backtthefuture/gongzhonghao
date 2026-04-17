#!/usr/bin/env python3
"""ImgBB 图片上传模块。"""

import os
import sys
import base64
import json
import ssl
import time
import urllib.request
import urllib.parse

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_imgbb_key(config_path=None):
    """从 config.yaml 读取 ImgBB API key。"""
    config_path = config_path or os.path.join(SKILL_DIR, "config.yaml")
    with open(config_path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("api_key:") and "imgbb" not in line:
                continue
            if "api_key" in line and "imgbb" not in line.lower():
                continue
    # Simple parse
    with open(config_path, "r") as f:
        content = f.read()
    in_imgbb = False
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped == "imgbb:":
            in_imgbb = True
            continue
        if in_imgbb and "api_key" in stripped:
            val = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            return val
        if not line.startswith(" ") and stripped.endswith(":") and stripped != "imgbb:":
            in_imgbb = False
    return None


def upload_to_imgbb(filepath, name, api_key=None, max_retries=3):
    """上传图片到 ImgBB，返回公网 URL。支持指数退避重试。"""
    if api_key is None:
        api_key = load_imgbb_key()
    if not api_key:
        raise ValueError("ImgBB API key not found")

    with open(filepath, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    data = urllib.parse.urlencode({
        "key": api_key,
        "name": name,
        "image": b64,
    }).encode()

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                "https://api.imgbb.com/1/upload",
                data=data,
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=60, context=_ssl_ctx)
            result = json.loads(resp.read())
            if result.get("success"):
                return result["data"]["url"]
            raise RuntimeError(f"ImgBB API error: {result}")
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"  Retry {attempt+1}/{max_retries} after {wait}s: {e}")
                time.sleep(wait)
            else:
                raise


if __name__ == "__main__":
    filepath = sys.argv[1]
    name = sys.argv[2]
    key = sys.argv[3] if len(sys.argv) > 3 else None
    print(upload_to_imgbb(filepath, name, api_key=key))

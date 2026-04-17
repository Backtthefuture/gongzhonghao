#!/usr/bin/env python3
"""Fetch content records from Feishu Bitable.

Standalone version - no external dependencies (requests/yaml).
All config read from the skill's own config.yaml.

Usage:
    python3 fetch_feishu.py --limit 20 --output /tmp/records.json
    python3 fetch_feishu.py --record-id recXXX --output /tmp/single.json
"""

import argparse
import json
import os
import ssl
import sys
from urllib import request
from urllib.error import HTTPError

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SSL context for environments with expired certs
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


def load_config():
    """Load config from config.yaml using simple parser (no PyYAML needed)."""
    config_path = os.path.join(SKILL_DIR, "config.yaml")
    if not os.path.exists(config_path):
        print(f"ERROR: config.yaml not found at {config_path}", file=sys.stderr)
        sys.exit(1)

    config = {}
    current_section = None
    with open(config_path, "r", encoding="utf-8") as f:
        for line in f:
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
    return config


def get_token(app_id, app_secret):
    """Get Feishu tenant access token."""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
    req = request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with request.urlopen(req, timeout=30, context=_ssl_ctx) as resp:
        data = json.loads(resp.read())
    if data.get("code") != 0:
        print(f"ERROR: Failed to get token: {data}", file=sys.stderr)
        sys.exit(1)
    return data["tenant_access_token"]


def extract_text(field_value):
    """Extract plain text from Feishu field value (handles str, dict, list)."""
    if field_value is None:
        return ""
    if isinstance(field_value, str):
        return field_value
    if isinstance(field_value, dict):
        return field_value.get("text") or field_value.get("link") or ""
    if isinstance(field_value, list):
        parts = []
        for item in field_value:
            if isinstance(item, dict):
                parts.append(item.get("text", ""))
            else:
                parts.append(str(item))
        return "".join(parts)
    return str(field_value)


def get_field_mapping(config):
    """Build field mapping dict from config."""
    mapping = {}
    prefix = "field_mapping."
    for key, val in config.items():
        if key.startswith(prefix):
            field_name = key[len(prefix):]
            mapping[field_name] = val
    return mapping


def fetch_records(token, base_id, table_id, field_mapping, limit=50):
    """Fetch records from Feishu Bitable with pagination, newest first."""
    records = []
    page_token = None

    sort_field = field_mapping.get("submitted_time", "提交时间")
    sort_payload = {"sort": [{"field_name": sort_field, "desc": True}]}

    while True:
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_id}/tables/{table_id}/records/search"
        page_size = min(limit * 2, 100) if limit else 100
        params = f"page_size={page_size}"
        if page_token:
            params += f"&page_token={page_token}"

        full_url = f"{url}?{params}"
        payload = json.dumps(sort_payload).encode()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        req = request.Request(full_url, data=payload, headers=headers, method="POST")

        try:
            with request.urlopen(req, timeout=30, context=_ssl_ctx) as resp:
                data = json.loads(resp.read())
        except HTTPError as e:
            print(f"ERROR: Feishu API returned {e.code}", file=sys.stderr)
            break

        if data.get("code") != 0:
            print(f"ERROR: Feishu API error: {data.get('msg')}", file=sys.stderr)
            break

        items = data.get("data", {}).get("items", [])
        for item in items:
            fields = item.get("fields", {})
            record_id = item.get("record_id", "")

            submitted_time_field = field_mapping.get("submitted_time", "提交时间")
            submitted_time_raw = fields.get(submitted_time_field)
            record_submitted_time = int(submitted_time_raw) if isinstance(submitted_time_raw, (int, float)) else 0

            title = extract_text(fields.get(field_mapping.get("title", "标题")))
            content = extract_text(fields.get(field_mapping.get("content", "摘要正文")))

            if not content or len(content) < 100:
                continue

            # Cover image attachment
            cover_field = field_mapping.get("cover", "封面图")
            cover_raw = fields.get(cover_field)
            cover_url = ""
            if isinstance(cover_raw, list) and len(cover_raw) > 0:
                first_att = cover_raw[0]
                if isinstance(first_att, dict):
                    cover_url = first_att.get("tmp_url", "")

            # Publish time (Feishu stores date as UTC midnight ms timestamp)
            publish_time_field = field_mapping.get("publish_time", "发布时间")
            publish_time_raw = fields.get(publish_time_field)
            publish_time = None
            if isinstance(publish_time_raw, (int, float)):
                publish_time = int(publish_time_raw)

            record = {
                "record_id": record_id,
                "title": title,
                "content": content,
                "guest": extract_text(fields.get(field_mapping.get("guest", "嘉宾"))),
                "source": extract_text(fields.get(field_mapping.get("source", "来源平台"))),
                "original_link": extract_text(fields.get(field_mapping.get("original_link", "原内容链接"))),
                "cover_image_url": cover_url,
                "publish_time": publish_time,
                "submitted_time": record_submitted_time,
                "quotes": [],
            }

            for i in range(1, 6):
                key = f"quote{i}"
                if key in field_mapping:
                    q = extract_text(fields.get(field_mapping[key]))
                    if q:
                        record["quotes"].append(q)

            records.append(record)

        has_more = data.get("data", {}).get("has_more", False)
        page_token = data.get("data", {}).get("page_token")

        if not has_more or (limit and len(records) >= limit):
            break

    records = records[:limit] if limit else records
    return records


def main():
    parser = argparse.ArgumentParser(description="Fetch Feishu Bitable records")
    parser.add_argument("--limit", type=int, default=20, help="Max records to fetch")
    parser.add_argument("--record-id", type=str, help="Fetch a specific record by ID")
    parser.add_argument("--output", type=str, help="Output JSON file path")
    args = parser.parse_args()

    config = load_config()

    app_id = config.get("feishu.app_id", "")
    app_secret = config.get("feishu.app_secret", "")
    base_id = config.get("bitable.base_id", "")
    table_id = config.get("bitable.table_id", "")

    if not all([app_id, app_secret, base_id, table_id]):
        print("ERROR: Missing feishu/bitable config in config.yaml", file=sys.stderr)
        sys.exit(1)

    field_mapping = get_field_mapping(config)

    print("Authenticating with Feishu...", file=sys.stderr)
    token = get_token(app_id, app_secret)
    print("Fetching records...", file=sys.stderr)

    records = fetch_records(token, base_id, table_id, field_mapping, args.limit)

    if args.record_id:
        records = [r for r in records if r["record_id"] == args.record_id]

    print(f"Found {len(records)} records with content", file=sys.stderr)

    output = json.dumps(records, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Saved to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate AI infographic images via YouMind CLI (createChat + imageGenerate).

Replaces the previous yunwu.ai chat-completions backend. Uses YouMind's
imageGenerate tool with hard-coded "个性化信息图" parameters so every image
carries 黄叔 avatar + consistent flat business illustration style.

The previous yunwu implementation is preserved in image_generator.py.yunwu.bak.

Usage:
    python3 image_generator.py \
        --prompt "信息图：AI效率革命核心三要素..." \
        --output "outputs/article_img1.png" \
        [--title "..."] \
        [--aspect-ratio 16:9] \
        [--timeout 300]
"""

import argparse
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


BOARD_ID = "019b39d0-9cc6-739b-861d-3db6f2bb7acf"
AVATAR_URL = (
    "https://cdn.gooo.ai/user-files/"
    "dc4140f7019261986af4f60c5de0c176a45a801b35a329b8d2df0bc74c925746@chat"
)
PERSONA = (
    "卡通化的亚洲男性，黑色整齐短发，穿着浅蓝色衬衫，温和的微笑，"
    "成熟稳重的气质，扁平插画风格"
)
IMAGE_MODEL = "gemini-3.1-flash-image-preview"

SKILL_REF_PATH = (
    Path(__file__).resolve().parent.parent
    / "references"
    / "youmind-infographic-skill.md"
)


def load_skill_instructions() -> str:
    """Load the full YouMind 个性化信息图 Skill text inline.

    We don't use atReferences[CraftDto] because the model sometimes fails to
    load it (see memory: feedback_youmind_infographic). Inlining the full
    Skill content guarantees the design guidelines (color palette, layout
    types, prompt template) are always present.
    """
    if SKILL_REF_PATH.exists():
        return SKILL_REF_PATH.read_text(encoding="utf-8")
    return ""  # fall back to hard-coded minimal guidelines below


MESSAGE_TEMPLATE = """你将按照下方【信息图生成器 Skill 指令】的完整规则，为这次任务生成 **一张** 信息图。

====================【信息图生成器 Skill 指令】====================

{skill_instructions}

====================【本次任务】====================

本次只生成 **1 张** 信息图，请直接按 Skill 步骤 4.3-4.5 执行：
1. 识别内容的逻辑结构（对比/流程/结构/层次/概念解释/案例）
2. 按 Skill 的 prompt 模板构建详细的英文/中文混合 prompt（必须包含分区描述、标题、标签、总结金句）
3. 直接调用 imageGenerate 工具

⚠️ 跳过 todoWrite、文档分析、用户确认等批量流程步骤——这是单图直出场景。

章节/内容输入：
{user_prompt}

====================【强制要求 - 必须严格遵守】====================

调用 imageGenerate 工具时，必须传入以下参数：
- model: "{image_model}"
- aspect_ratio: "{aspect_ratio}"
- quality: "high"
- source_image_urls: ["{avatar_url}"]   ← 黄叔头像参考图，必填！
- title: "{title}"

⚠️ prompt 里必须包含这段人物特征描述（Skill 里也有强调）：
『{persona}』
"""

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


def youmind_call(api: str, payload: dict, timeout: int = 180) -> dict:
    """Invoke `youmind call <api>` with JSON payload, parse stdout as JSON."""
    if not os.environ.get("YOUMIND_API_KEY"):
        print("ERROR: YOUMIND_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    r = subprocess.run(
        ["youmind", "call", api, json.dumps(payload)],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if r.returncode != 0:
        raise RuntimeError(
            f"youmind {api} failed (exit {r.returncode}): {r.stderr.strip()}"
        )
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"youmind {api} returned non-JSON: {r.stdout[:300]}"
        ) from e


def create_image_chat(user_prompt: str, title: str, aspect_ratio: str) -> dict:
    msg = MESSAGE_TEMPLATE.format(
        user_prompt=user_prompt,
        title=title,
        aspect_ratio=aspect_ratio,
        avatar_url=AVATAR_URL,
        persona=PERSONA,
        image_model=IMAGE_MODEL,
        skill_instructions=load_skill_instructions(),
    )
    payload = {
        "boardId": BOARD_ID,
        "mode": "chat",
        "chatModel": IMAGE_MODEL,
        "message": msg,
        "tools": {
            "imageGenerate": {
                "useTool": "required",
                "aspectRatio": aspect_ratio,
                "quality": "high",
                "model": IMAGE_MODEL,
            }
        },
    }
    return youmind_call("createChat", payload, timeout=120)


def poll_until_done(chat_id: str, poll: int = 4, timeout: int = 300) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        data = youmind_call("listMessages", {"chatId": chat_id}, timeout=60)
        last = data["messages"][-1]
        status = last.get("status")
        if status == "success":
            return last
        if status == "failed":
            err = last.get("error") or last.get("blocks", [])
            raise RuntimeError(f"chat failed: {json.dumps(err, ensure_ascii=False)[:400]}")
        time.sleep(poll)
    raise TimeoutError(f"chat {chat_id} did not finish within {timeout}s")


def extract_image_block(message: dict, prefer_original: bool = False) -> tuple[str, dict]:
    """Find the successful image_generate tool block.

    Returns (image_url, tool_arguments). By default prefers `image_urls`
    (compressed, ~hundreds of KB) because WeChat renders <2MB images
    reliably but rejects/timeouts on large originals. Pass prefer_original
    only when full fidelity is needed (e.g. print).
    """
    for block in message.get("blocks", []):
        if (
            block.get("type") == "tool"
            and block.get("toolName") == "image_generate"
            and block.get("status") == "success"
        ):
            result = block.get("toolResult") or {}
            if prefer_original:
                urls = result.get("original_image_urls") or result.get("image_urls") or []
            else:
                urls = result.get("image_urls") or result.get("original_image_urls") or []
            if urls:
                return urls[0], (block.get("toolArguments") or {})
    raise RuntimeError("no successful image_generate block found in assistant reply")


def verify_hard_requirements(tool_args: dict) -> None:
    """Warn if the model ignored the hard-coded requirements."""
    src = tool_args.get("source_image_urls") or tool_args.get("sourceImageUrls") or []
    if not src:
        print(
            "⚠️ WARN: source_image_urls missing — 头像参考未生效，出图可能不像黄叔",
            file=sys.stderr,
        )
    prompt = tool_args.get("prompt", "") or ""
    if "卡通化的亚洲男性" not in prompt:
        print("⚠️ WARN: persona description missing from tool prompt", file=sys.stderr)


def download(url: str, out_path: str) -> None:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "wechat-article-generator/1.0"})
    with urllib.request.urlopen(req, timeout=60, context=_ssl_ctx) as resp:
        data = resp.read()
    out.write_bytes(data)


def infer_title_from_output(output_path: str) -> str:
    """Derive a short title from the output filename (SLUG_imgN_keyword.png)."""
    stem = Path(output_path).stem
    parts = stem.split("_")
    # Keep last segment as keyword if present
    if len(parts) >= 3 and parts[-2].startswith("img"):
        return parts[-1] or stem
    return stem


def main():
    ap = argparse.ArgumentParser(
        description="Generate infographic images via YouMind imageGenerate"
    )
    ap.add_argument("--prompt", required=True, help="Image generation prompt")
    ap.add_argument("--output", required=True, help="Output PNG path")
    ap.add_argument("--title", default=None, help="Image title (default: from filename)")
    ap.add_argument(
        "--aspect-ratio",
        default="16:9",
        choices=["1:1", "2:3", "3:2", "4:3", "3:4", "9:16", "16:9", "21:9"],
    )
    ap.add_argument("--timeout", type=int, default=300, help="Total timeout in seconds")
    ap.add_argument(
        "--original", action="store_true",
        help="Download original uncompressed image (WARNING: can be 10MB+, WeChat may reject)",
    )
    # Accept --model/--retry for backwards compat with pipeline; they're ignored.
    ap.add_argument("--model", default=None, help="(ignored, kept for compat)")
    ap.add_argument("--retry", type=int, default=1, help="Retry on failure")
    args = ap.parse_args()

    title = args.title or infer_title_from_output(args.output)

    print(f"[youmind] prompt: {args.prompt[:80]}...", file=sys.stderr)
    print(f"[youmind] output: {args.output}", file=sys.stderr)
    print(f"[youmind] title:  {title}  aspect: {args.aspect_ratio}", file=sys.stderr)

    last_err = None
    for attempt in range(1, args.retry + 1):
        try:
            chat = create_image_chat(args.prompt, title, args.aspect_ratio)
            cid = chat["id"]
            print(f"[youmind] chat {cid} created (attempt {attempt}/{args.retry})", file=sys.stderr)

            msg = poll_until_done(cid, timeout=args.timeout)
            url, tool_args = extract_image_block(msg, prefer_original=args.original)
            verify_hard_requirements(tool_args)

            print(f"[youmind] downloading {url}", file=sys.stderr)
            download(url, args.output)
            print(f"[youmind] saved to {args.output}", file=sys.stderr)
            print(args.output)
            return
        except Exception as e:
            last_err = e
            print(f"[youmind] attempt {attempt} failed: {e}", file=sys.stderr)
            if attempt < args.retry:
                time.sleep(2 ** attempt)

    print(f"FAILED: {last_err}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()

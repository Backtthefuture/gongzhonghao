#!/usr/bin/env python3
"""End-to-end pipeline for wechat-article-generator.

Input: a markdown file with image placeholders like:
  ![图注](slug_img1_keyword.png)

What it does:
1. Parse markdown image placeholders
2. Generate a simple English prompt for each image based on nearby section context + template hints
3. Call image_generator.py to materialize missing images
4. Run convert.js to render HTML

Goal: make the advertised "auto image generation" actually happen.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
REF_PROMPTS = SKILL_DIR / 'references' / 'image-prompt-templates.md'
IMG_GEN = SKILL_DIR / 'scripts' / 'image_generator.py'
CONVERT = SKILL_DIR / 'scripts' / 'convert.js'

STYLE_SUFFIX = (
    " Style requirements: Clean, minimalist infographic illustration; "
    "flat design with simple geometric shapes; limited color palette with dark navy, orange and teal; "
    "white or light gray background; Chinese text labels if needed; no photorealistic elements; "
    "no 3D effects; no gradients; aspect ratio 16:9 landscape."
)


def load_markdown(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def split_sections(md: str):
    parts = re.split(r'(?m)^##\s+', md)
    sections = []
    if parts:
        first = parts[0].strip()
        if first:
            sections.append(("引言", first))
        for chunk in parts[1:]:
            lines = chunk.splitlines()
            title = lines[0].strip() if lines else '章节'
            body = '\n'.join(lines[1:]).strip()
            sections.append((title, body))
    return sections


def extract_image_placeholders(md: str):
    return list(re.finditer(r'!\[([^\]]*)\]\(([^)]+)\)', md))


def find_context_for_image(md: str, img_start: int):
    before = md[:img_start]
    sections = split_sections(before)
    if not sections:
        return "引言", before[-500:]
    return sections[-1]


def build_prompt(caption: str, filename: str, section_title: str, section_body: str) -> str:
    keyword = Path(filename).stem.split('_')[-1]
    body = re.sub(r'\s+', ' ', section_body)
    body = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', body)
    body = body[:500]

    lower = f"{section_title} {caption} {keyword} {body}".lower()
    if any(k in lower for k in ['对比', 'vs', '差异', '新旧']):
        shape = 'Create a side-by-side comparison infographic.'
    elif any(k in lower for k in ['流程', '步骤', '路径', '闭环', 'pipeline']):
        shape = 'Create a process infographic with 3 to 5 connected steps.'
    elif any(k in lower for k in ['边界', '约束', '安全', 'intent']):
        shape = 'Create a boundary infographic showing visible vs restricted zones.'
    elif any(k in lower for k in ['数字', '%', '倍', '万', '亿']):
        shape = 'Create a statistic-focused infographic highlighting key numbers.'
    else:
        shape = 'Create a concept infographic with one central idea and 3 supporting elements.'

    return (
        f"{shape} Main topic: {section_title}. "
        f"Caption: {caption or keyword}. "
        f"Use this article context: {body}."
        + STYLE_SUFFIX
    )


def ensure_images(md_path: Path):
    md = load_markdown(md_path)
    placeholders = extract_image_placeholders(md)
    generated = []
    for m in placeholders:
        caption, rel_path = m.group(1).strip(), m.group(2).strip()
        img_path = (md_path.parent / rel_path).resolve()
        if img_path.exists():
            continue
        section_title, section_body = find_context_for_image(md, m.start())
        prompt = build_prompt(caption, rel_path, section_title, section_body)
        img_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [sys.executable, str(IMG_GEN), '--prompt', prompt, '--output', str(img_path)]
        print(f'[image] generating: {img_path.name}', file=sys.stderr)
        subprocess.run(cmd, check=True)
        generated.append(str(img_path))
    return generated


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True, help='Markdown file path')
    ap.add_argument('--output', required=True, help='Output dir for HTML')
    ap.add_argument('--filename', default=None, help='Optional output HTML filename')
    args = ap.parse_args()

    md_path = Path(args.input).resolve()
    out_dir = Path(args.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    generated = ensure_images(md_path)
    print(f'[pipeline] generated {len(generated)} images', file=sys.stderr)

    cmd = ['node', str(CONVERT), '--input', str(md_path), '--output', str(out_dir), '--images', 'embed']
    if args.filename:
        cmd += ['--filename', args.filename]
    subprocess.run(cmd, check=True)
    print('[pipeline] done', file=sys.stderr)


if __name__ == '__main__':
    main()

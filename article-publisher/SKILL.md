# 发布管家 - Article Publisher

将公众号母稿排版、配图、生成封面，发布到草稿箱。

## 触发场景

- article-writer 完成母稿后用户说"发布"
- "帮我排版发布"
- "发到公众号草稿箱"
- `/article-publisher`
- `/发布`

## 不触发场景

- 还没有母稿（先用 article-writer 生成）
- 只想派生其他平台版本不想发公众号（article-writer 内置了派生能力）

## 工作流

### Step 1: 定位母稿

检查以下位置，找到要发布的母稿：
1. 对话上下文中 article-writer 刚生成的文件路径
2. 用户指定的文件名/选题名
3. `01-内容生产/选题管理/01-待深化选题/` 中最近修改的 .md
4. `01-内容生产/选题管理/02-已发布选题/` 中 status 为待发布的

找到后读取母稿内容，确认标题和核心内容。

### Step 1.5: 对抗式审核检查（强制关卡）

⚠️ **不管母稿从哪来的（article-writer 生成、手写、对话中产出），发布前必须确认对抗式内容审核已执行。**

检查方式：
1. 回顾当前对话上下文，是否已经执行过 article-writer 的 Step 3（对抗式内容审核）
2. 如果已执行且评分 ≥ 8 分：向用户展示审核结果摘要，确认发布
3. **如果未执行：必须先执行对抗式审核，不能跳过直接发布**

执行对抗式审核的方法（参考 article-writer Step 3）：
1. 参谋角色从五个维度（标题与开场、结构与逻辑、数据与可信度、读者价值、篇幅与节奏）逐一攻击文章
2. 笔杆子角色根据攻击报告修改
3. 裁判角色评分（0-10），低于 8 分打回重写，最多循环 3 轮
4. 通过后向用户确认："对抗式审核通过（X/10 分，共 N 轮）。确认发布《{标题}》到公众号草稿箱？"

> **为什么加这个关卡**：实际踩过的坑——手写母稿后直接说"发布"，跳过了质量审核，导致文章质量关卡缺失。对抗式审核确保无论母稿来源如何，发布前的质量标准一致。

#### 对抗式审核执行纪律（防走过场）

> **历史踩坑**：2026-03-28~30 杭州期间连续发布多篇文章，对抗式审核流于形式——参谋没有真正尖锐攻击，裁判评分偏宽松，角色没有严格分离。原因：用户在赶路/疲惫时说"发布"，AI 倾向于快速通过。

**硬约束（不可违反）：**

1. **参谋必须找到至少 1 个"不通过"的维度**。如果五个维度全部通过，说明参谋没有认真找问题——重新审视，提高标准。完美的初稿不存在。
2. **参谋的输出必须包含具体的问题描述和改进要求**。不能只写"通过"或"不错"，每个维度必须有具体内容。
3. **笔杆子必须实际修改文章**。不能只说"参谋说的对"然后不改。至少改 1 处。
4. **裁判评分不能全部 9/10**。五个维度中至少有 1 个低于 9 分，并说明为什么。
5. **用户催促时不能降低标准**。即使用户说"快点发布"，也必须完成完整的参谋攻击→笔杆子修改→裁判评分流程。可以精简输出格式，但不能跳过步骤。

### Step 2: 归档到已发布选题

如果母稿还在 `01-待深化选题/`，先归档：
1. 在 `02-已发布选题/` 创建文件夹 `{日期}-{标题}/`
2. 将母稿移入并重命名为 `公众号.md`
3. 创建 `_meta.md`（参见 CLAUDE.md 中的模板）

### Step 3: AI 配图

扫描母稿中的图片占位符 `![图注](SLUG_imgN_keyword.png)`：
1. 结合图片所在章节标题、图注、临近正文上下文，生成英文 prompt
2. 调用图片生成能力生成配图
3. 风格：扁平极简，2-3 色，与文章主题匹配
4. **配图生成使用 `image_generator.py`**：
```bash
python3 ~/.agents/skills/wechat-article-generator/scripts/image_generator.py \
  --prompt "{英文prompt}" \
  --output "outputs/images/{SLUG}_imgN.png"
```
5. 多张图可并行生成（使用后台命令），提高效率

⚠️ **重要**：如果母稿中没有图片占位符，pipeline 会跳过配图（输出 "generated 0 images"）。此时必须：
1. 根据文章内容规划 3-4 张配图位置（每 500-800 字一张）
2. 手动生成配图
3. 将图片转 base64 嵌入 HTML

### Step 3.5: HTML 排版（关键步骤）

⚠️ **不要直接使用 `run_pipeline.py` 的 HTML 输出作为最终版本**。pipeline 的 convert.js 无法正确处理非标准 Markdown 格式（如自定义 PART 编号、金句高亮框等），会导致输出变成无样式的纯文本。

**必须手写 HTML**，严格遵循 `theme-default.css` 的设计系统。

#### 必读：theme-default.css 设计规范

文件位置：`~/.agents/skills/wechat-article-generator/assets/theme-default.css`

发布前**必须**先读取该文件，确保 HTML 使用正确的设计系统。以下是核心组件（所有样式必须内联，不能用 class）：

##### 1. Hero 开篇区域（必须有，深色背景）

```html
<section style="background-color: #1a1a2e; color: #ffffff; padding: 56px 24px 44px; text-align: center;">
  <span style="display: block; width: 40px; height: 4px; background-color: #e76f51; margin: 0 auto 24px;"></span>
  <p style="font-size: 26px; font-weight: bold; line-height: 1.5; color: #ffffff; margin-bottom: 12px; letter-spacing: 1px;">{主标题/副标题}</p>
  <p style="font-size: 14px; color: #999999; margin-bottom: 0; letter-spacing: 0.5px;">{系列名或描述}</p>
</section>
```

##### 2. PART 章节标题（杂志风格）

```html
<section style="margin-top: 48px; margin-bottom: 24px;">
  <p style="font-size: 36px; font-weight: bold; color: #f5d0c5; letter-spacing: 2px; line-height: 1; margin: 0;">01</p>
  <p style="font-size: 11px; font-weight: bold; color: #e76f51; letter-spacing: 4px; margin: 0;">PART</p>
  <span style="display: block; width: 100%; height: 1px; background-color: #e8e8e8; margin: 10px 0;"></span>
  <p style="font-size: 20px; font-weight: bold; color: #1a1a2e; line-height: 1.4; margin: 0;">{章节标题}</p>
</section>
```

##### 3. 正文段落

```html
<p style="margin-bottom: 18px; text-align: justify; font-size: 16px; color: #333333; line-height: 2.0;">{正文}</p>
```

##### 4. 强调体系（5 级）

```html
<!-- L1 荧光笔：绝对核心洞察 -->
<span style="background-color: #fff3b0; padding: 2px 4px; font-weight: bold; color: #1a1a2e;">{文字}</span>

<!-- L2 加粗+下划线：次要重点 -->
<span style="font-weight: bold; color: #1a1a2e; border-bottom: 2px solid #e76f51; padding-bottom: 1px;">{文字}</span>

<!-- L3 品牌色：品牌/主题强调 -->
<strong style="color: #e76f51; font-weight: bold;">{文字}</strong>

<!-- L4 普通加粗 -->
<strong style="color: #1a1a2e; font-weight: bold;">{文字}</strong>

<!-- L5 行内代码：技术术语 -->
<span style="background-color: #f3f4f6; color: #e76f51; padding: 2px 6px; border-radius: 3px; font-size: 14px; font-family: 'SF Mono','Fira Code','Consolas',monospace;">{术语}</span>
```

##### 5. 核心洞察卡片（hbox，深色背景）

用于金句、核心观点等需要视觉突出的内容：

```html
<section style="background-color: #1a1a2e; color: #ffffff; padding: 24px 20px; border-radius: 8px; margin: 28px 0; font-size: 16px; line-height: 1.9; border-left: 4px solid #e76f51;">
  <p style="margin: 0; color: #ffffff;">{核心洞察内容}</p>
</section>
```

##### 6. 引用块

```html
<p style="margin: 24px 0; padding: 18px 20px; background-color: #f9f9f9; border-left: 3px solid #cccccc; font-size: 15px; color: #666666; line-height: 1.8;">{引用内容}</p>
```

##### 7. 代码块

```html
<pre style="margin: 20px 0; padding: 20px; background-color: #1a1a2e; color: #a8d8a8; font-family: 'SF Mono','Menlo','Consolas',monospace; font-size: 13px; line-height: 1.8; border-radius: 8px; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word;">{代码内容}</pre>
```

##### 8. 表格

```html
<table style="width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px;">
  <thead>
    <tr>
      <th style="background-color: #1a1a2e; color: #ffffff; padding: 12px 16px; text-align: left; font-weight: bold;">{表头}</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="padding: 12px 16px; border-bottom: 1px solid #eee; color: #333333;">{内容}</td>
      <!-- 需要强调的列用橙色 -->
      <td style="padding: 12px 16px; border-bottom: 1px solid #eee; color: #e76f51; font-weight: bold;">{强调内容}</td>
    </tr>
  </tbody>
</table>
```

##### 9. 配图嵌入

```html
<section style="margin: 28px 0; text-align: center;">
  <img src="data:image/png;base64,{BASE64}" style="max-width: 100%; height: auto; border-radius: 6px;">
  <p style="font-size: 12px; color: #aaaaaa; margin-top: 8px; text-align: center;">{图注}</p>
</section>
```

##### 10. 分隔线

```html
<section style="text-align: center; margin: 40px 0;">
  <span style="display: block; width: 48px; height: 2px; background-color: #e0e0e0; margin: 0 auto;"></span>
</section>
```

##### 11. 结尾区域

```html
<!-- 橙色分隔线 -->
<section style="text-align: center; padding: 36px 0 16px; margin-top: 48px;">
  <span style="display: block; width: 48px; height: 2px; background-color: #e76f51; margin: 0 auto 24px;"></span>
</section>

<!-- 结尾金句卡片（如有） -->
<section style="background-color: #1a1a2e; color: #ffffff; padding: 24px 20px; border-radius: 8px; margin: 28px 0; font-size: 16px; line-height: 1.9; border-left: 4px solid #e76f51; text-align: center;">
  <p style="font-size: 18px; font-weight: bold; color: #ffffff; margin: 0; line-height: 1.8;">{结尾金句}</p>
</section>

<!-- 署名 -->
<p style="font-size: 15px; color: #666666; text-align: center; margin-top: 20px; line-height: 1.8;">{署名信息}</p>
```

#### 配色表

| 用途 | 色值 |
|------|------|
| 深色背景（hero、hbox、代码块、表头） | `#1a1a2e` |
| 品牌橙色（强调、装饰线、PART标记） | `#e76f51` |
| 淡橙色（PART大号数字） | `#f5d0c5` |
| 青色（副标题、子标题边框） | `#2a9d8f` |
| 正文黑色 | `#333333` |
| 正文灰色（次要信息） | `#666666` |
| 引用/说明灰色 | `#999999` / `#aaaaaa` |

### Step 4: 封面生成

从文章中提取封面要素：
- **标签行**：2-3 个英文关键词
- **主标题**：分 2-3 行，关键实体用橙色 `#e76f51`，概念用青色 `#2a9d8f`
- **标签胶囊**：2-3 个核心数据点
- **配色**：深蓝 `#0a0f1a` 底 + 橙 + 青

输出 `outputs/{SLUG}_cover.html`，比例 2.35:1

封面 HTML 需要用 Playwright 转为 PNG 后才能上传：
```python
python3 -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1200, 'height': 510})
    page.goto('file:///path/to/cover.html')
    page.screenshot(path='/tmp/{SLUG}_cover.png')
    browser.close()
"
```

### Step 5: 发布到草稿箱

发布脚本：
```bash
python3 ~/.agents/skills/wechat-article-generator/scripts/publish_to_wechat.py \
  --html "outputs/wechat/{SLUG}_article.html" \
  --cover "/tmp/{SLUG}_cover.png" \
  --title "文章标题" \
  --summary "120字以内摘要" \
  --slug "{SLUG}"
```

⚠️ 发布脚本会自动将 HTML 中的 base64 图片上传到 ImgBB 图床并替换为 URL，无需手动处理。

如果发布脚本不可用，输出文件路径，让用户手动复制粘贴到公众号后台。

### Step 6: 更新 _meta.md

更新对应选题文件夹的 `_meta.md`：
- 公众号 status → 已发布
- 记录发布日期
- 提醒用户 3 天后补充数据

### Step 7: 展示结果

```
## 公众号文章已发布

### 草稿箱状态
- publicationId: {id}（如有）
- 登录公众号后台 → 内容管理 → 草稿箱 查看

### 文件
- 文章 HTML：outputs/wechat/{SLUG}_article.html
- 封面：outputs/{SLUG}_cover.html
- 母稿：02-已发布选题/{日期}-{标题}/公众号.md

### 配图
- 生成了 N 张配图

---

后续你可以：
- 说「出小红书版」→ 从母稿派生（调用 article-writer）
- 说「出视频脚本」→ 从母稿派生
- 说「反向编译」→ 把这篇文章的知识资产回流到知识库（推荐！）
- 3 天后说「补充数据：{标题}」→ 记录阅读量等数据

💡 建议反向编译这篇文章——把核心观点、有效表达、方法论提取到知识库，让下次创作更有积累。
```

## 依赖

### 可选依赖（有则用，无则降级）
- `wechat-article-generator` 的 `image_generator.py` — AI 配图生成
- `wechat-article-generator` 的 `publish_to_wechat.py` — 发布到草稿箱
- `wechat-article-generator` 的 `config.yaml` — API 密钥配置
- `wechat-article-generator` 的 `theme-default.css` — **设计系统参考（必读）**
- `playwright` — 封面 HTML 转 PNG

### 降级方案
如果上述脚本不可用：
1. 配图：使用其他可用的图片生成 skill（gemini-image、baoyu-image-gen 等）
2. 排版：手动编写内联样式 HTML（参考 Step 3.5 的组件规范）
3. 发布：输出最终 HTML 文件，用户手动复制到公众号后台

## 注意事项

1. **发布前必须确认**——不要未经确认就发布
2. **HTML 验证**——无 `<style>` 标签、无 `linear-gradient`、无 `<div>`（用 `<section>` 替代）、图片已嵌入
3. **不修改母稿内容**——本 skill 只负责排版和发布，不改写内容
4. **保持文件整洁**——所有输出文件放在对应选题文件夹或 outputs/ 下
5. **必须使用 theme-default.css 的设计系统**——不要自己发明样式，所有组件都有对应规范

## 历史踩坑记录

> 以下问题已在实际发布中遇到过，务必避免。

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 文章没有配图 | 母稿没写图片占位符，pipeline 输出 "generated 0 images" | 必须检查母稿是否有占位符，没有则手动规划并生成 |
| HTML 无样式，全是纯文本 | 直接使用 `run_pipeline.py` 输出，它的 convert.js 无法处理非标准 Markdown | 不依赖 pipeline 的 HTML，手写内联样式 HTML |
| 开篇没有深色背景 | 没有使用 hero 区域组件 | 文章开头必须有 hero section（`#1a1a2e` 背景） |
| PART 编号样式错误 | 用了自创的橙色小标签，而非设计系统的杂志风格 | 使用 theme 中的 `.sh` 样式：大号淡色数字 + 小号橙色 PART + 分隔线 |
| 核心洞察没有视觉突出 | 用了普通灰底引用框 | 核心洞察/金句用 hbox 组件（`#1a1a2e` 背景 + `#e76f51` 左边框） |
| 封面上传失败 | 直接传了 HTML 文件，ImgBB 需要图片格式 | 封面 HTML 必须先用 Playwright 转为 PNG |
| 对抗式审核被跳过 | 手写母稿后直接说"发布"，article-publisher 不检查 article-writer 的流程是否完成 | 在 Step 1.5 加了强制检查关卡，不管母稿来源如何，发布前必须确认对抗式内容审核已执行 |
| 对抗式审核走过场 | 杭州期间连续发布多篇，参谋没有真正攻击（五维度全"通过"、没有具体问题），裁判评分偏宽（都给8.5-9分），用户催促时降低标准 | 加了5条硬约束：参谋必须找到≥1个不通过、必须有具体问题、笔杆子必须实际改、裁判不能全9分、用户催促不能降标准 |

# 黄叔公众号写作 Skills

一套为公众号内容创作打造的 Claude Code Skills，覆盖 **选题打磨 → 写作 → 发布** 的完整流水线。

作者：[@黄叔](https://github.com/Backtthefuture)

---

## 三个 Skill

### 1. topic-partner（选题伙伴）
把碎片想法通过对话打磨成结构化选题卡，自动关联素材库。

**触发**：「记录选题：xxx」「帮我打磨这个选题」「/topic-partner」

### 2. article-writer（文章写手)
从选题卡或想法生成公众号母稿，遵循黄叔文风，对抗式三角色审稿（笔杆子 / 参谋 / 裁判）。
内置平台派生：「出小红书版」「出视频脚本」「出播客版」。

**触发**：「直接写吧」「写文章：xxx」「/article-writer」

### 3. article-publisher（发布管家）
母稿排版 + AI 配图 + 封面生成，发布到公众号草稿箱。

**触发**：「发布」「发到公众号草稿箱」「/article-publisher」

---

## 工作流串联

```
topic-partner → article-writer → article-publisher
  选题对话         写母稿              排版发布
```

一个选题从想法到发布全自动衔接，也可以在任一阶段停下。

---

## 仓库结构

```
gongzhonghao/
├── topic-partner/          # Skill 1：选题对话
├── article-writer/         # Skill 2：母稿写作 + 三角色审稿
├── article-publisher/      # Skill 3：排版 + 配图 + 发布
└── wechat-tools/           # 发布管家依赖的脚本与样式
    ├── scripts/
    │   ├── publish_to_wechat.py    # 调微信草稿箱 API
    │   ├── image_generator.py      # AI 配图（YouMind CLI）
    │   ├── upload_imgbb.py         # 图床上传
    │   ├── convert.js              # Markdown → HTML
    │   ├── run_pipeline.py         # 一键流水线
    │   ├── text_rewriter.py        # 文字改写（可选）
    │   └── fetch_feishu.py         # 飞书多维表格拉素材（可选）
    ├── assets/
    │   └── theme-default.css       # 公众号 HTML 设计系统
    ├── config.yaml.example         # 配置模板
    └── package.json
```

---

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/Backtthefuture/gongzhonghao.git
cd gongzhonghao
```

### 2. 安装三个 Skill

```bash
# 用户级（所有项目都能用）
cp -r topic-partner article-writer article-publisher ~/.claude/skills/

# 或项目级（只在当前项目生效）
mkdir -p your-project/.claude/skills
cp -r topic-partner article-writer article-publisher your-project/.claude/skills/
```

### 3. 安装发布工具链

`article-publisher` 里的脚本路径默认指向 `~/.agents/skills/wechat-article-generator/`。把 `wechat-tools/` 放到这个位置：

```bash
mkdir -p ~/.agents/skills
cp -r wechat-tools ~/.agents/skills/wechat-article-generator
# 或者用软链：ln -s "$(pwd)/wechat-tools" ~/.agents/skills/wechat-article-generator
```

### 4. 安装依赖

```bash
cd ~/.agents/skills/wechat-article-generator

# Node 依赖（convert.js 用）
npm install

# Python 依赖：大部分脚本只用标准库
# image_generator.py 需要 YouMind CLI（详见"个性化配置"）
```

### 5. 配置密钥

```bash
cd ~/.agents/skills/wechat-article-generator
cp config.yaml.example config.yaml
# 编辑 config.yaml，填入你的 API key
```

需要的密钥（最少必填前两个）：

| 配置 | 说明 | 申请地址 |
|------|------|----------|
| `wechat_api.api_key` | 微信公众号 API（默认走 limyai 代理；自建方案可换 base_url） | [wx.limyai.com](https://wx.limyai.com) |
| `imgbb.api_key` | ImgBB 图床（用于把文章 base64 图片上传成 URL） | [api.imgbb.com](https://api.imgbb.com/) |
| `image_api.api_key` | AI 配图（可选，需要外部 API） | yunwu.ai 或自选 |
| `text_api.api_key` | 文字改写（可选） | yunwu.ai 或自选 |
| `feishu.app_id/secret` | 飞书拉素材（可选） | [open.feishu.cn](https://open.feishu.cn) |

---

## 个性化配置

### AI 配图（image_generator.py）

默认走 [YouMind](https://youmind.ai) CLI，并硬编码了"黄叔风格"的头像和 persona。
要让配图变成你自己的风格，编辑 `wechat-tools/scripts/image_generator.py` 顶部：

```python
BOARD_ID = "你的 YouMind boardId"
AVATAR_URL = "你的头像 URL"
PERSONA = "你的卡通形象描述"
```

并设置环境变量 `YOUMIND_API_KEY`。

**没有 YouMind？** 把 article-publisher 的配图步骤换成任意可用的图片生成 skill（如 `gemini-image`、`baoyu-image-gen`）。SKILL.md 已注明这是降级路径。

### 文风（article-writer）

`article-writer/SKILL.md` 里的"黄叔文风"章节是给我用的硬规则。你 fork 后改成自己的文风规则即可。

### 知识库路径（topic-partner / article-writer）

skill 里引用了我自己的知识库结构（`01-内容生产/选题管理/...`、`00-我/...`）。
你换成自己的目录结构，或者直接删除"检索素材库"相关步骤。

---

## 一键安装脚本

```bash
git clone https://github.com/Backtthefuture/gongzhonghao.git
cd gongzhonghao
cp -r topic-partner article-writer article-publisher ~/.claude/skills/
mkdir -p ~/.agents/skills
cp -r wechat-tools ~/.agents/skills/wechat-article-generator
cd ~/.agents/skills/wechat-article-generator
cp config.yaml.example config.yaml
npm install
# 然后编辑 config.yaml 填密钥
```

重启 Claude Code，对话中说 `/topic-partner`、`/article-writer`、`/article-publisher` 即可触发。

---

## 许可

MIT

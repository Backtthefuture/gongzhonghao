# 黄叔公众号写作 Skills

一套为公众号内容创作打造的 Claude Code Skills，覆盖 **选题打磨 → 写作 → 发布** 的完整流水线。

作者：[@黄叔](https://github.com/Backtthefuture)

---

## 三个 Skill

### 1. topic-partner（选题伙伴）
把碎片想法通过对话打磨成结构化选题卡，自动关联素材库。

**触发**：「记录选题：xxx」「帮我打磨这个选题」「/topic-partner」

### 2. article-writer（文章写手)
从选题卡或想法生成公众号母稿，遵循黄叔文风，十维度自检。
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

## 安装方式

### 方式一：克隆到 Claude Code skills 目录

```bash
# 用户级（所有项目都能用）
cd ~/.claude/skills
git clone https://github.com/Backtthefuture/gongzhonghao.git
mv gongzhonghao/{topic-partner,article-writer,article-publisher} .
rm -rf gongzhonghao

# 或项目级（只在当前项目生效）
cd your-project/.claude/skills
git clone https://github.com/Backtthefuture/gongzhonghao.git
mv gongzhonghao/{topic-partner,article-writer,article-publisher} .
rm -rf gongzhonghao
```

### 方式二：手动下载

下载三个 skill 文件夹，放进 `~/.claude/skills/` 目录即可。

安装后重启 Claude Code，在对话中说 `/topic-partner`、`/article-writer`、`/article-publisher` 即可触发。

---

## 许可

MIT

# baoge AI Codex Guide

面向中文用户的 Codex 公开教程与实战案例库。

## 本地预览

```bash
python3 -m http.server 8765
```

然后打开：

```text
http://localhost:8765/
```

## 在线访问

仓库推送到 GitHub 后，在仓库 Settings -> Pages 中开启 GitHub Pages：

- Source: Deploy from a branch
- Branch: main
- Folder: / (root)

开启后访问：

```text
https://yintianbao9-rgb.github.io/codex/
```

## 每日自动更新

仓库内置 GitHub Actions：

```text
.github/workflows/daily-update.yml
```

它会每天 UTC 00:10 自动运行：

```bash
python scripts/collect_codex_updates.py --site-dir . --output-dir updates/archive
```

输出：

- `data/codex_update_sources.json`：网站自动读取的最新采集数据
- `updates/archive/YYYY.../summary.md`：每次抓取摘要
- `updates/index.html`：公开可看的自动更新报告页

公开报告页：

```text
https://yintianbao9-rgb.github.io/codex/updates/
```

手动触发：进入 GitHub 仓库 -> Actions -> Daily Codex and AI industry update -> Run workflow。

## 目录

- `index.html`：网站首页
- `tutorials/`：01-19 单节教程页面
- `assets/`：图片与 SVG 素材
- `data/`：Codex 更新采集数据
- `contribute.html`：共建与更新说明

# 🤖 agent-hunter

全球 AI Agent 产品检索与追踪工具。自动发现、更新和报告 AI 编程工具，生成可视化全景报告。

## 功能特性

- 🔍 **多源搜索** — 360搜索（中文）+ DuckDuckGo（英文），完全免费
- 🤖 **LLM 智能提取** — 自动从搜索结果中识别 AI Agent 产品并结构化数据
- 📊 **HTML 报告** — 卡片式可视化报告，按分类展示产品全景
- 💾 **增量更新** — SHA256 哈希缓存，只处理变化的条目
- 📁 **JSON 数据源** — 每个 agent 一个独立 JSON 文件，易于维护和扩展

## 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/xiowen/agent-hunter.git
cd agent-hunter

# 安装依赖
pip install -r requirements.txt

# 复制配置文件
cp config.json.example config.json
```

### 配置

编辑 `config.json`，填写 LLM API 配置：

```json
{
  "llm": {
    "base_url": "https://your-api-endpoint.com/anthropic",
    "api_key": "your-api-key-here",
    "model": "MiniMax-M2.7"
  }
}
```

> 支持 Anthropic 兼容 API 格式（如 MiniMax、Claude 等）。

### 运行

```bash
# 默认：搜索发现 + 更新 + 生成报告
python run.py

# 仅搜索发现新 agent
python run.py discover

# 仅增量更新已有数据
python run.py update

# 仅生成 HTML 报告
python run.py report

# 强制全部更新 + 报告
python run.py force

# 查看所有 agent
python run.py list

# 查看缓存状态
python run.py status
```

### 输出

- `agents/*.json` — 每个 agent 的独立数据文件
- `report/index.html` — 可视化 HTML 报告
- `cache/meta.json` — 缓存元数据（哈希、更新时间）

## 搜索源

| 源 | 语言 | 覆盖站点 | 费用 |
|---|------|---------|------|
| 360搜索 | 中文 | 知乎/微信公众号/掘金/CSDN等 | 免费 |
| DuckDuckGo | 英文 | ProductHunt/HackerNews/Medium/GitHub等 | 免费 |
| Firecrawl | 中英文 | 可自定义 | 需 API key |

在 `config.json` 的 `search_sources` 中可开关各搜索源。

## 项目结构

```
agent-hunter/
├── agents/              # agent 数据（每个 agent 一个 JSON）
├── cache/               # 缓存元数据
├── report/              # 生成的 HTML 报告
├── hunter.py            # 核心：搜索、更新、缓存逻辑
├── report_gen.py        # HTML 报告生成
├── run.py               # 主入口
├── config.json          # 配置文件（需自行创建）
├── config.json.example  # 配置模板
└── requirements.txt     # Python 依赖
```

## Agent 数据格式

每个 `agents/*.json` 文件包含以下字段：

```json
{
  "id": "cursor",
  "name": "Cursor",
  "category": "IDE",
  "description": "AI 优先的代码编辑器，内置代码补全和对话功能",
  "features": ["代码补全", "对话编辑", "代码库索引"],
  "open_source": "no",
  "license": "专有",
  "strengths": ["编辑器体验", "代码理解", "多文件编辑"],
  "position": "AI 原生 IDE",
  "website": "https://cursor.com",
  "docs_url": "https://docs.cursor.com",
  "github_repo": "",
  "pricing": "免费+付费",
  "tags": ["IDE", "AI", "编辑器"],
  "last_verified": "2026-05-17"
}
```

## 定时运行

使用 cron 每日自动运行：

```bash
# 编辑 crontab
crontab -e

# 添加每日凌晨 2 点运行
0 2 * * * cd /path/to/agent-hunter && python run.py >> /var/log/agent-hunter.log 2>&1
```

## License

[MIT](LICENSE)

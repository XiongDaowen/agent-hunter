import sys
from datetime import datetime

log_path = sys.argv[1]
job_id = sys.argv[2] if len(sys.argv) > 2 else "cron-unknown"

now = datetime.now().strftime("%Y-%m-%d %H:%M")

entry = """

## {now}（Job ID: {job_id}）

### 本次分析
- 检查对象：webui.py, report_gen.py, news.py, hunter.py, config.json
- 发现的问题：
  1. Streamlit WebUI（webui.py）agent 卡片标题只显示名称，缺少分类图标
  2. report_gen.py TOP5 已生效（iteration 17），分类图标在 HTML 报告生效，但 Streamlit 卡片标题未同步
  3. firecrawl 仍为 disabled（402），360+DDG fallback 正常
  4. discover 未发现新 agent（搜索正常）
- 决定动手的改进点：在 Streamlit agent 卡片标题旁添加分类图标（与 report/index.html 一致）

### 本次修复
- webui.py:438 — 在 agent 卡片标题前添加分类图标，从 CATEGORY_ICONS 映射获取
  - 列表顶部已预计算 cat_icon 变量（用于分类标题），现已在容器内重新获取当前 agent 的 cat_icon
  - 图标对应：💻IDE/⌨️CLI/🖥️TUI/🎨GUI/🔌Plugin/📦SDK/⚙️Runtime/🤖Other

### 验证结果
- python3 -m py_compile hunter.py report_gen.py news.py webui.py → 全部通过
- python3 run.py report → 成功生成 report/index.html（78个产品）
- discover 运行正常，未发现新 agent（360+HN fallback 正常）

### 待下次修复
1. meta.json 只跟踪 11 个 agent，需扩展到全部 78 个
2. firecrawl 402 问题是否可换用其他付费方案（如已解决可恢复主源）
3. 29 个闭源商业产品（Cursor/Copilot/Claude Code 等）的 github_repo 字段空白问题
""".format(now=now, job_id=job_id)

with open(log_path, "a") as f:
    f.write(entry)

print("Appended to " + log_path)
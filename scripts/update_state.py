import json

state = {
  "iteration_count": 20,
  "last_run": "2026-05-25",
  "done_categories": [
    "数据分类准确性 - 将 Manus 从 Other 改为 GUI（云端 Web 平台）",
    "数据分类准确性 - 将 Tabby 从 Plugin 改为 SDK（自托管服务）",
    "数据分类准确性 - 将 MCP 从 Runtime 改为 SDK（协议标准 + 多语言 SDK）",
    "LLM 调用优化 - 添加指数退避重试、429/5xx 差异化处理、ProxyError/ConnectionError 专门处理、连接10s/读取60s 超时分隔",
    "LLM 调用优化 - 添加 JSON 修复函数 _safe_json_parse，修复 LLM 返回的语法错误（缺少引号、缺少逗号、尾随逗号、单引号等）",
    "Streamlit WebUI 优化 - 添加模糊搜索功能（difflib.SequenceMatcher，阈值50%），添加「仅开源」快速过滤 toggle",
    "报告质量优化 - 添加分类颜色 CSS（IDE紫、CLI绿、TUI紫红、GUI粉、Plugin橙、SDK蓝、Runtime黄、Other灰），在卡片标题旁显示分类标签",
    "搜索源优化 - 新增 5 个中文搜索词（Cursor 替代、AI代码审查、AI编程开源、AI agent框架、Claude Code 替代）和 5 个英文搜索词（Cursor alternative、AI code review、open source AI CLI、AI programmer assistant、multi-agent framework）",
    "数据完整性优化 - discover 发现 FlowScript，修复 docs_url 缺失（FlowScript 添加 GitHub README 链接）",
    "数据完整性优化 - 修复 Flexpilot、YA Copilot、Toad 的 github_repo 和 license（Flexpilot: open_source=no→yes, license=专有→MIT, 添加 GitHub 链接; YA Copilot: license=未知→MIT, 添加 GitHub 链接; Toad: license=未知→MIT, 添加 docs_url）",
    "Streamlit WebUI 优化 - 新增「仅显示有 GitHub」过滤 toggle，新增「按许可证」和「按最近更新」排序选项，顶部指标栏新增「有 GitHub」计数卡片",
    "数据完整性调研 - 发现 29/78 个 agent 缺少 github_repo 字段（多为闭源商业产品如 Cursor、Copilot、Claude Code 等；开源产品如 Tabby、Auto-coder 已补全）",
    "Streamlit WebUI 优化 - 修复 agent_hot_score 函数注释（中文改为英文，类型安全说明更清晰）",
    "数据完整性优化 - 修复 9 个 agent 的 license 字段（从「未知」改为 Unknown）：AgentArmor, AutoGPT Platform, Claude Bootstrap, Droid, hai-cli, Sidekick, SuperLocalMemoryV2, Vectimus, Zep — 统一英文格式",
    "report_gen.py:218-290 — 新增 TOP5 排名 CSS 样式（.top5-section/.top5-list/.top5-rank/.rank-1/.rank-2/.rank-3 等）；report_gen.py:547-596 — 新增 compute_hot_score() 和 render_top5_section() 函数，在每个分类标题下方渲染热度TOP5排名（按github_repo/tags/features加权），15个分类区块均已生效；discover 未发现新agent（360+HN搜索正常）",
    "报告质量优化 - 在 report/index.html 统计栏新增「有 GitHub」计数卡片（49个）",
    "Streamlit WebUI 搜索优化 - 重写搜索逻辑为多层级匹配（name权重100/description权重60/tags权重40），组合分数取max；同时添加 _search_score 和 _name_score 到 agent 对象供排序使用；降低阈值从30到25以提高搜索宽容度",
    "Streamlit WebUI 搜索优化 - 重构搜索逻辑：搜索词先.strip()防空格误匹配；复用已有fuzzy_score()函数（消除重复SequenceMatcher代码）；desc_score×0.6降权，tags_score×0.4再降权；combined_score=max(name,desc,tags)；阈值保持25",
    "代码注释国际化 - 将 webui.py:agent_hot_score 和 report_gen.py:compute_hot_score/render_top5_section 的中文注释全部改为英文，提升代码可读性和专业度",
    "Streamlit WebUI 优化 - 在 agent 卡片标题旁添加分类图标（IDE/CLI/TUI/GUI/Plugin/SDK/Runtime/Other），使分类导航更直观，提升视觉层次感",
    "数据完整性优化 - 补充 7 个开源 agent 的 docs_url 字段（AgentArmor, Claude Bootstrap, Go-TUI, Hai-CLI, Sidekick, SuperLocalMemoryV2, Vectimus），补全 website 字段（agentarmor/go-tui）",
    "Streamlit WebUI TOP5 排名 - 新增 render_webui_top5() 函数，在选择单个分类时通过 st.expander 显示该分类热度 TOP5 排名（与 HTML 报告的 compute_hot_score 逻辑保持一致），用户点击分类后展开即可查看"
  ],
  "failed_patterns": [],
  "notes": "firecrawl 仍为disabled（402），360+DDG fallback 正常；report 生成成功（78个产品）；webui.py 新增 TOP5 分类热度排名 expander"
}

with open('/home/xiowen/.hermes/scripts/agent-evolution-state.json', 'w') as f:
    json.dump(state, f, ensure_ascii=False, indent=2)
print('done')
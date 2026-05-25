import json

state_file = '/home/xiowen/.hermes/scripts/agent-evolution-state.json'
with open(state_file) as f:
    state = json.load(f)

state['iteration_count'] = 30
state['last_run'] = '2026-05-25'
state['done_categories'].append('WebUI 资讯渲染优化 - 将 st.html() 内联渲染替换为正则解析+Streamlit 原生组件渲染（st.expander/columns/markdown），避免 st.html() 在某些环境下的兼容性问题')

with open(state_file, 'w') as f:
    json.dump(state, f, ensure_ascii=False, indent=2)

print("Updated: iteration_count=30")
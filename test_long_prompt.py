import requests
cfg = {
    "base_url": "https://ark.cn-beijing.volces.com/api/coding/v3",
    "api_key": "ark-dd5ccd59-ec1f-461a-bf1c-8c55098cedbe-4da6a",
    "model": "ark-code-latest"
}
url = f"{cfg['base_url']}/chat/completions"
headers = {
    "Authorization": f"Bearer {cfg['api_key']}",
    "content-type": "application/json"
}

# 模拟 discover 中的 prompt
system_prompt = """你是一个专业的 AI Agent 产品研究员。"""

user_content = """请分析以下网页搜索结果，识别并提取 AI Agent 产品信息：

来源1: 知乎 - 标题: 2025年最佳AI编程助手推荐 - Cursor IDE 是一款基于 AI 的代码编辑器，集成 GPT-4， 能够自动补全代码、生成函数、解释代码。GitHub Copilot 是微软推出的 AI 编程助手。

来源2: 掘金 - 标题: AI Agent 开发框架哪家强 - LangChain 是一个用于构建 LLM 应用的开发框架，提供了 Agent 组件。AutoGPT 是一个实验性的开源项目。"""

body = {
    "model": cfg["model"],
    "max_tokens": 4000,
    "temperature": 0.1,
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]
}
print(f"Prompt size: system={len(system_prompt)}, user={len(user_content)}")
print("Starting request...") 
try:
    resp = requests.post(url, headers=headers, json=body, timeout=30)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"Response length: {len(content) if content else 0}")
        print(f"Response: {content[:300] if content else 'EMPTY'}")
    else:
        print(f"Response: {resp.text[:500]}")
except requests.exceptions.Timeout:
    print("TIMEOUT")
except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}")
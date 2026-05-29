#!/bin/bash
# Verify dead links with curl (following redirects, longer timeout)
cd /home/xiowen/agent-hunter

agents=(
  "AgentArmor|https://github.com/Agastya910/agentarmor"
  "Anthropic MCP Servers|https://github.com/modelcontextprotocol"
  "AutoGen|https://microsoft.github.io/autogen"
  "ChatGPT Code / Canvas|https://chatgpt.com"
  "Claude Bootstrap|https://github.com/alinaqi/claude-bootstrap"
  "CodeGPT|https://www.codegpt.com"
  "DeepSeek-Reasonix|https://esengine.github.io/DeepSeek-Reasonix/"
  "DeerFlow|https://github.com/bytedance/deer-flow"
  "Devika|https://devika.ai"
  "FlowScript|https://github.com/phillipclapham/flowscript"
  "Gemini CLI|https://ai.google.dev/gemini-api/docs/code-execution"
  "GitHub Copilot|https://github.com/features/copilot"
  "Google Gemini Code Assist|https://cloud.google.com/code-assist"
  "Goose|https://block.github.io/goose"
  "LangChain|https://langchain.com"
  "LangGraph|https://langchain.com/langgraph/"
  "OpenAI Agents SDK|https://openai.com/index/openai-agents-sdk"
  "OpenAI Codex CLI|https://openai.com/codex"
  "Sidekick|https://cesarandreslopez.github.io/sidekick-agent-hub/"
  "Smolagents|https://huggingface.co/docs/smolagents"
  "SuperLocalMemoryV2|https://github.com/varun369/SuperLocalMemoryV2"
  "Toad|https://github.com/batrachianai/toad"
  "Vectimus|https://github.com/vectimus/vectimus"
  "hai-cli|https://github.com/braincore/hai-cli"
)

for entry in "${agents[@]}"; do
  name="${entry%%|*}"
  url="${entry#*|}"
  echo -n "[$name] $url => "
  result=$(curl -sIL --max-time 15 "$url" 2>&1 | grep -E "^HTTP" | tail -1)
  if [ -z "$result" ]; then
    echo "NO RESPONSE"
  else
    echo "$result"
  fi
done
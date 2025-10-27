#!/bin/bash
# ============================================
# RD-Agent 环境变量配置脚本（Qwen 全家桶版）
# 聊天 + 向量 都使用阿里云 DashScope 官方接口
# ============================================

# ✅ 聊天模型（Qwen）
export CHAT_MODEL="qwen-plus"
# 国内用户：dashscope.aliyuncs.com
# 国际版用户：dashscope-intl.aliyuncs.com
export OPENAI_API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1"
# ⚠️ 替换成你自己的 DashScope API Key
export OPENAI_API_KEY="sk-aca2359331ba4d0895cf5e7966a31e57"

# ✅ 向量模型（Qwen 官方提供）
# 说明：text-embedding-v4 是 Qwen 最新 embedding 模型
# 也可以使用 text-embedding-v3 等旧版
export EMBEDDING_MODEL="text-embedding-v4"

# 🧠 可选参数（非必填）
# 如果你用带思维链 <think> 的模型，可以打开以下选项
# export REASONING_THINK_RM=True

# 🌐 若在公司代理环境，可取消注释以下两行：
# export http_proxy="http://proxy.host:port"
# export https_proxy="http://proxy.host:port"

echo "✅ 已成功加载 Qwen 环境变量！"
echo "当前 Chat 模型: $CHAT_MODEL"
echo "当前 Embedding 模型: $EMBEDDING_MODEL"
echo "API Base: $OPENAI_API_BASE"
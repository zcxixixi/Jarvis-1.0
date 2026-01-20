# JARVIS 快速开始指南 🚀

欢迎使用贾维斯AI助手！这个指南将帮助你在5分钟内启动你的AI助手。

## 📋 前置要求

- ✅ Python 3.10+ （你的Mac已有）
- ✅ Grok API Key （需要获取）

## 🔑 获取 Grok API Key

1. 访问 [x.ai Console](https://console.x.ai/)
2. 登录你的账号
3. 创建新的API密钥
4. 复制密钥（新用户有$25免费额度！）

## ⚡ 安装步骤

### 1. 进入项目目录

```bash
cd ~/ai-agents-for-beginners/jarvis-assistant
```

### 2. 安装依赖

```bash
pip3 install -r requirements.txt
```

### 3. 配置API密钥

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 文件
nano .env  # 或用 VSCode: code .env
```

在 `.env` 文件中设置你的API密钥：
```
GROK_API_KEY=xai-你的密钥
```

保存并退出（nano: Ctrl+O, Enter, Ctrl+X）

### 4. 运行贾维斯！

```bash
python3 jarvis_cli.py
```

## 💬 使用示例

启动后，你就可以和贾维斯对话了：

```
您: 你好，贾维斯
贾维斯: 您好，先生。贾维斯已就绪，随时为您服务。有什么可以帮助您的吗？

您: 现在几点了？
贾维斯: 当前时间是 19:39

您: 帮我写一段Python代码
贾维斯: 当然，请告诉我您需要什么功能的代码...
```

## 🎮 特殊命令

- `exit` / `quit` / `退出` - 退出程序
- `clear` / `清空` - 清空对话历史
- `stats` / `统计` - 查看对话统计

## 🛠️ 故障排除

### 问题1: ModuleNotFoundError

```bash
# 确保使用Python 3
python3 --version

# 重新安装依赖
pip3 install -r requirements.txt
```

### 问题2: API Key错误

检查 `.env` 文件中的 `GROK_API_KEY` 是否正确设置

### 问题3: 网络问题

确保你的Mac可以访问 `api.x.ai`

## 📚 下一步

- ✅ 你已经完成了 Phase 1：Mac文本原型
- ⏭️ Phase 2：等硬件到了，添加语音功能
- ⏭️ Phase 3：智能家居集成
- ⏭️ Phase 4：部署到树莓派

## 🆘 需要帮助？

遇到问题？直接问我！我会帮你解决。

---

**享受你的贾维斯吧！** 🤖✨

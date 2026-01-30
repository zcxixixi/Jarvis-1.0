# Jarvis 1.0 - AI Voice Assistant

一个基于混合架构的中文AI语音助手，支持语音唤醒、意图识别、工具调用和自然语音合成。

## 🚀 快速开始

```bash
# 1. 安装依赖
pip install -r jarvis_assistant/requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 API keys

# 3. 运行
python3 main.py

# 4. 说出唤醒词
"Hey Jarvis"
```

## 📁 项目结构

```
jarvis/
├── main.py                    # 入口文件
├── jarvis_assistant/          # 核心代码
│   ├── core/                 # 核心组件
│   │   ├── hybrid_jarvis.py  # 主系统（S2S + Agent）
│   │   ├── agent.py          # Agent大脑
│   │   ├── query_router.py   # 意图路由
│   │   └── intent_classifier.py  # 意图分类器
│   ├── plugins/              # 工具插件（31个）
│   ├── services/             # 外部服务（TTS/ASR）
│   └── config/               # 配置文件
├── docs/                     # 文档
│   ├── CONNECT_PI.md        # 树莓派部署指南
│   ├── TEST_SUITE.md        # 测试套件说明
│   └── WORK_SUMMARY.md      # 工作总结
├── tests/                    # 测试脚本
│   ├── test_e2e_pipeline.py # 端到端测试
│   ├── test_record_voice.py # 录音工具
│   └── test_voice_pipeline.py # 语音流程测试
├── scripts/                  # 辅助脚本
├── .agent/skills/           # 开发规范
└── venv/                    # 虚拟环境

```

## ✨ 核心功能

- **🎤 语音唤醒**: "Hey Jarvis" 唤醒词检测
- **🧠 智能路由**: 自动判断简单对话 vs 复杂查询
- **🔧 31个工具**: 天气、股票、智能家居、音乐等
- **🔊 自然语音**: 基于豆包TTS的高质量语音合成
- **⚡ 低延迟**: S2S快速路径 + Agent深度处理

## 🛠️ 支持的查询

### 简单对话（S2S快速响应）
- "你好"
- "现在几点"
- "谢谢"

### 复杂查询（Agent + 工具）
- "北京天气怎么样" → 天气API
- "特斯拉股价" → 股票API
- "黄金价格" → 金融API
- "打开客厅的灯" → 智能家居
- "播放音乐" → 音乐播放

## 📝 开发指南

详见 `.agent/skills/jarvis-development/SKILL.md`

### 添加新工具

1. 在 `jarvis_assistant/plugins/` 创建工具文件
2. 在 `intent_classifier.py` 添加关键词到 `TOOL_KEYWORDS`
3. 测试：`python3 main.py`

**重要**: 工具关键词必须加到 `TOOL_KEYWORDS`，不要加到 `SIMPLE_PATTERNS`

## 🧪 测试

```bash
# 端到端测试
python3 tests/test_e2e_pipeline.py

# 录制语音
python3 tests/test_record_voice.py

# 完整语音流程
python3 tests/test_voice_pipeline.py
```

## 🌲 部署到树莓派

详见 `docs/CONNECT_PI.md`

```bash
# 复制文件
scp -r jarvis_assistant/ main.py .env shumeipai@192.168.31.150:~/jarvis-assistant/

# 启动服务
ssh shumeipai@192.168.31.150 "cd ~/jarvis-assistant && nohup python3 main.py > jarvis.log 2>&1 &"
```

## 📊 系统架构

```
用户语音 → 唤醒词检测 → ASR识别 → Intent分类
                                      ↓
                            ┌─────────┴─────────┐
                            ↓                   ↓
                       简单对话              复杂查询
                         (S2S)              (Agent)
                            ↓                   ↓
                      快速响应            工具调用
                            ↓                   ↓
                            └─────────┬─────────┘
                                      ↓
                                  TTS合成
                                      ↓
                                  语音输出
```

## 🔧 技术栈

- **语音识别**: 豆包 ASR
- **语音合成**: 豆包 TTS V3 (SeedTTS 2.0)
- **LLM**: 豆包 Realtime API
- **唤醒词**: OpenWakeWord
- **音频**: PyAudio
- **工具**: 31个自定义插件

## 📄 许可证

MIT License

## 🙏 致谢

- 豆包 Realtime API
- OpenWakeWord
- 所有开源贡献者

---

**版本**: 1.0 (Stable)  
**最后更新**: 2026-01-30

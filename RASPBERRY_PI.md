# 树莓派部署指南 🥧

## ⏱️ 时间估算

**总时间: 约30-45分钟**

- ✅ 系统准备: 10分钟
- ✅ 代码部署: 5分钟
- ✅ 依赖安装: 10-15分钟
- ✅ 测试运行: 5分钟
- ✅ 蓝牙音箱配对: 5-10分钟

## 📋 前置要求

### 你的树莓派需要：
- ✅ 树莓派 3/4/5 (任何版本都行)
- ✅ 已安装 Raspberry Pi OS
- ✅ 联网（WiFi或网线）
- ✅ SSH已启用（或接显示器）

### 硬件（暂时不需要）：
- ⏭️ 麦克风（Phase 2再说）
- ✅ 小米蓝牙音箱（你已有）

## 🚀 快速部署步骤

### 1. 连接到树莓派

在你的Mac终端：

```bash
# 找到树莓派IP（或用 raspberrypi.local）
ssh pi@raspberrypi.local
# 默认密码通常是 raspberry
```

### 2. 更新系统（可选但推荐）

```bash
sudo apt update
sudo apt upgrade -y
```

### 3. 安装系统依赖（关键）

树莓派上安装 `pyaudio` 需要一些底层的开发库：

```bash
sudo apt update
sudo apt install python3-pip libportaudio2 libportaudio-dev portaudio19-dev python3-pyaudio -y
```

### 4. 从 Git 同步代码

在树莓派上：

```bash
cd ~
git clone https://github.com/zcxixixi/Jarvis-1.0.git
cd Jarvis-1.0
```

### 5. 安装 Python 依赖

```bash
pip3 install -r requirements.txt
```

### 6. 测试运行！

```bash
python3 hybrid_jarvis.py
```

如果您看到“Jarvis is alive”，说明基础运行环境已就绪。

### 7. 配置API密钥

```bash
# 编辑 .env 文件
nano .env
```

添加你的Grok API Key，然后保存（Ctrl+O, Enter, Ctrl+X）

### 8. 再次测试运行！

```bash
python3 hybrid_jarvis.py
```

如果看到贾维斯的界面，恭喜你成功了！🎉

## 🔊 配对蓝牙音箱（可选）

### 步骤：

```bash
# 1. 进入蓝牙配对模式
bluetoothctl

# 2. 在bluetoothctl中执行：
power on
agent on
default-agent
scan on

# 3. 把小米音箱设置为配对模式
# 4. 找到音箱的MAC地址（类似 XX:XX:XX:XX:XX:XX）

# 5. 配对和连接
pair XX:XX:XX:XX:XX:XX
trust XX:XX:XX:XX:XX:XX
connect XX:XX:XX:XX:XX:XX

# 6. 退出
exit
```

### 更新 .env 配置

把音箱MAC地址添加到 `.env`：
```
BLUETOOTH_SPEAKER_MAC=XX:XX:XX:XX:XX:XX
```

## 🔄 设置开机自启（可选）

让贾维斯在树莓派启动时自动运行：

```bash
# 创建systemd服务
sudo nano /etc/systemd/system/jarvis.service
```

粘贴以下内容：

```ini
[Unit]
Description=JARVIS AI Assistant
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/jarvis-assistant
ExecStart=/usr/bin/python3 /home/pi/jarvis-assistant/jarvis_cli.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl enable jarvis.service
sudo systemctl start jarvis.service

# 查看状态
sudo systemctl status jarvis.service
```

## 📊 测试清单

- [ ] SSH连接到树莓派成功
- [ ] Python 3.9+ 已安装
- [ ] 代码成功传输
- [ ] 依赖安装完成
- [ ] .env 配置正确
- [ ] jarvis_cli.py 运行成功
- [ ] 可以正常对话
- [ ] （可选）蓝牙音箱已配对

## 🛠️ 故障排除

### 问题1: SSH连接失败

```bash
# 在树莓派上启用SSH（需要接显示器）
sudo raspi-config
# Interface Options -> SSH -> Enable
```

### 问题2: 依赖安装慢

树莓派性能较弱，安装依赖可能需要10-15分钟，耐心等待

### 问题3: 内存不足

如果树莓派内存只有1GB，考虑：
- 增加swap空间
- 使用更轻量的模型

### 问题4: 蓝牙配对失败

```bash
# 重启蓝牙服务
sudo systemctl restart bluetooth
```

## ⚡ 性能对比

| 设备 | 启动时间 | 响应速度 | 功耗 |
|------|---------|---------|------|
| Mac | <1秒 | 快 | 高 |
| 树莓派5 | 2-3秒 | 快 | 低 |
| 树莓派4 | 3-5秒 | 中等 | 低 |
| 树莓派3 | 5-8秒 | 较慢 | 低 |

## 🎯 下一步

部署成功后：
1. ✅ 先在Mac上测试对话功能
2. ✅ 部署到树莓派运行
3. ⏭️ 添加麦克风实现语音输入
4. ⏭️ 连接蓝牙音箱输出
5. ⏭️ 添加唤醒词
6. ⏭️ 24小时运行

---

**你现在就可以开始部署了！整个过程大约30-45分钟。**

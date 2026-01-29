# 树莓派连接指南 (Raspberry Pi Connection Guide)

本文档旨在帮助 AI 助手和开发者快速连接并管理运行 Jarvis 的树莓派。

## 1. 基本连接信息 (Basic Info)

*   **设备 IP**: `192.168.31.150`
*   **用户名 (User)**: `shumeipai`
*   **SSH 端口**: `22` (默认)
*   **工作目录**: `/home/shumeipai/jarvis-assistant`

## 2. SSH 免密登录配置 (SSH Key Setup)

为了让 AI 助手能够自动部署代码和运行命令，**必须**配置 SSH 免密登录。

### 步骤:
1.  **在本地机器生成密钥** (如果还没有):
    ```bash
    ssh-keygen -t rsa -b 4096
    ```
2.  **将公钥复制到树莓派**:
    ```bash
    ssh-copy-id shumeipai@192.168.31.150
    ```
    *(这一步需要输入树莓派密码)*

3.  **验证连接**:
    ```bash
    ssh shumeipai@192.168.31.150
    ```
    如果不需要输入密码直接进入，则配置成功。

## 3. AI 助手常用命令 (Common Commands)

AI 助手在操作时，应使用以下标准命令格式。

### 3.1 部署代码 (Deploy Code)
将本地修改的文件同步到树莓派：
```bash
scp -o StrictHostKeyChecking=no local_file.py shumeipai@192.168.31.150:~/jarvis-assistant/
```

### 3.2 重启 Jarvis 服务 (Restart Service)
停止旧进程并后台启动新进程：
```bash
ssh -o StrictHostKeyChecking=no shumeipai@192.168.31.150 "pkill -9 python3; cd ~/jarvis-assistant && nohup python3 -u hybrid_jarvis.py > jarvis.log 2>&1 &"
```

### 3.3 查看实时日志 (View Logs)
监控 Jarvis 的运行输出：
```bash
ssh -o StrictHostKeyChecking=no shumeipai@192.168.31.150 "tail -f ~/jarvis-assistant/jarvis.log"
```

### 3.4 检查进程状态 (Check Process)
确认 Jarvis 是否在运行：
```bash
ssh -o StrictHostKeyChecking=no shumeipai@192.168.31.150 "ps aux | grep python3 | grep hybrid_jarvis"
```

## 4. 树莓派环境 (Pi Environment)

*   **Python 版本**: Python 3.13.5
*   **音频系统**: 
    *   Audio Server: PulseAudio / Jack (可能存在配置冲突，目前使用 ALSA 兼容模式)
    *   播放器: `mpg123` (mp3), `mpv` (m4a/mp4), `aplay` (wav)
*   **依赖库**:
    *   `numpy`
    *   `websockets`
    *   `pyaudio`
    *   `openwakeword`
    *   `onnxruntime`
    *   `yt-dlp`
    *   `pyncm` (网易云音乐)

## 5. 常见问题 (Troubleshooting)

*   **连接超时 (Connection Timeout)**: 
    *   检查树莓派是否开机并连接到同一 WiFi。
    *   SSH 连接数可能过多，尝试等待几分钟或重启 SSH 服务。
*   **Permission Denied**: 
    *   检查 SSH 密钥是否正确配置。
    *   检查文件权限。

"""
Music Tools
Play local music files using macOS 'afplay'
"""
import os
import subprocess
import glob
import platform
from typing import Dict, List, Optional
from .base import BaseTool

class MusicPlayerTool(BaseTool):
    """Play local music"""
    
    # Simple state tracking (in-memory)
    _current_process: Optional[subprocess.Popen] = None
    _music_dir = os.path.expanduser("~/Music")
    
    @property
    def name(self) -> str:
        return "play_music"
    
    @property
    def description(self) -> str:
        return "播放本地音乐。支持操作：play(播放), stop(停止), list(列出), search(搜索)"
    
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["play", "stop", "list", "search"],
                            "description": "操作类型"
                        },
                        "query": {
                            "type": "string",
                            "description": "歌曲名称关键字（仅 play/search 时需要）"
                        }
                    },
                    "required": ["action"]
                }
            }
        }
    
    async def execute(self, **kwargs) -> str:
        """Execute music command"""
        action = kwargs.get("action")
        query = kwargs.get("query", "")
        
        if not action:
            return "❌ 错误：未指定 action"
        
        if action == "stop":
            if self._current_process:
                try:
                    self._current_process.terminate()
                except:
                    try: self._current_process.kill()
                    except: pass
                self._current_process = None
            
            # Force cleanup
            if platform.system() == "Linux":
                subprocess.run(["pkill", "-9", "mpv"], stderr=subprocess.DEVNULL)
                subprocess.run(["pkill", "-9", "mpg123"], stderr=subprocess.DEVNULL)

            return "⏹️ 音乐已停止"
            
        elif action == "list":
            files = self._scan_music()
            if not files:
                return "📂 音乐目录为空 (需要放在 ~/Music)"
            return "🎵 发现音乐：\n" + "\n".join([f"- {os.path.basename(f)}" for f in files[:10]])
            
        elif action == "search":
            files = self._scan_music(query)
            if not files:
                return f"❌ 未找到包含 '{query}' 的音乐"
            return f"🔎 搜索结果：\n" + "\n".join([f"- {os.path.basename(f)}" for f in files[:5]])
            
        elif action == "play":
            # 1. Stop ALL current audio (critical for preventing overlap)
            if self._current_process:
                try:
                    self._current_process.terminate()
                except:
                    self._current_process.kill()
            
            # Kill all audio players to ensure clean state
            if platform.system() == "Darwin":
                subprocess.run(["killall", "afplay"], stderr=subprocess.DEVNULL)
            else:  # Linux
                subprocess.run(["pkill", "-9", "mpv"], stderr=subprocess.DEVNULL)
                subprocess.run(["pkill", "-9", "mpg123"], stderr=subprocess.DEVNULL)
            
            # 2. Find file(s)
            # Special case for "all" or empty query for continuous play
            if not query or query.lower() in ["all", "随便", "全部", "列表"]:
                files = self._scan_music()
                is_playlist = True
            else:
                files = self._scan_music(query)
                is_playlist = False

            if not files:
                # 🎯 Fallback: Search Netease Cloud Music
                print(f"⚠️ Local music not found for '{query}', searching Netease Cloud...")
                try:
                    # Import here to avoid circular dependencies if any
                    from .netease_tools import NeteaseMusicTool
                    return await NeteaseMusicTool().execute(action="play", query=query)
                except Exception as e:
                    return f"❌ 未找到本地音乐且云端搜索失败: {str(e)}"
            
            # 3. Play
            try:
                if platform.system() == "Darwin":
                    # Darwin afplay doesn't support playlists easily, just play first
                    cmd = ["afplay", files[0]]
                else:
                    # Linux: use mpv for playlist/single, mpg123 for mp3
                    if is_playlist:
                        # Standardize music volume to 60 (out of 100)
                        cmd = ["mpv", "--volume=60", "--no-video", "--really-quiet", "--shuffle"] + files
                    elif files[0].endswith(".m4a") or files[0].endswith(".mp4"):
                        cmd = ["mpv", "--volume=60", "--no-video", "--really-quiet", files[0]]
                    else:
                        # Standardize mpg123 volume to approx 60% (~20000 / 32768)
                        cmd = ["mpg123", "-f", "20000", "-q", files[0]]
                        
                self._current_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                if is_playlist:
                    return f"▶️ 正在开启随机连播模式（共 {len(files)} 首）"
                return f"▶️ 正在播放：{os.path.basename(files[0])}"
            except Exception as e:
                return f"❌ 播放失败: {str(e)}"
                
        return f"❌ 未知操作: {action}"

    def _scan_music(self, query: str = "") -> List[str]:
        """Helper to find mp3/m4a/wav files"""
        extensions = ['*.mp3', '*.m4a', '*.wav', '*.flac']
        found = []
        for ext in extensions:
            # Check music dir
            found.extend(glob.glob(os.path.join(self._music_dir, ext)))
            # Also check subdirectories (depth 1)
            found.extend(glob.glob(os.path.join(self._music_dir, "*", ext)))
            
        if query:
            # Case insensitive search
            query = query.lower()
            found = [f for f in found if query in os.path.basename(f).lower()]
            
        return sorted(list(set(found)))

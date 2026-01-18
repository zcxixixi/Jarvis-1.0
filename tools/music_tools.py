"""
Music Tools
Play local music files using macOS 'afplay'
"""
import os
import subprocess
import glob
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
    
    async def execute(self, action: str, query: str = "") -> str:
        """Execute music command"""
        
        if action == "stop":
            if self._current_process:
                self._current_process.terminate()
                self._current_process = None
                return "⏹️ 音乐已停止"
            return "没有正在播放的音乐"
            
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
            # 1. Stop current
            if self._current_process:
                self._current_process.terminate()
                
            # 2. Find file
            files = self._scan_music(query)
            if not files:
                return f"❌ 未找到音乐: {query}"
            
            target_file = files[0]
            
            # 3. Play (Mac only)
            try:
                # Use afplay (built-in macOS command)
                # running in background so it doesn't block Jarvis
                self._current_process = subprocess.Popen(
                    ["afplay", target_file],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return f"▶️ 正在播放：{os.path.basename(target_file)}"
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

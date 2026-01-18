"""
Migu Music Tool (Ultimate Edition)
Sources:
1. Netease VIP (High Quality, if Cookie valid)
2. YouTube (Unlimited Library, via yt-dlp)
3. iTunes (Reliable Fallback, Preview)
"""
import os
import requests
import subprocess
from typing import Dict, Optional
from .base import BaseTool

class MiguMusicTool(BaseTool):
    """Play music from Cloud (Netease VIP / YouTube / iTunes)"""
    
    _cache_dir = os.path.expanduser("~/Music/JarvisCache")
    _current_process: Optional[subprocess.Popen] = None
    
    def __init__(self):
        if not os.path.exists(self._cache_dir):
            os.makedirs(self._cache_dir)
            
    @property
    def name(self) -> str:
        return "play_music_cloud"
    
    @property
    def description(self) -> str:
        return "从云端搜索并播放歌曲(支持网易云VIP/YouTube无限库)。"
    
    def get_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "歌曲名称关键字"
                        },
                        "action": {
                            "type": "string",
                            "enum": ["play", "stop"],
                            "description": "操作: play 或 stop"
                        }
                    },
                    "required": ["action"]
                }
            }
        }
    
    async def execute(self, action: str, query: str = "") -> str:
        if action == "stop":
            if self._current_process:
                self._current_process.terminate()
                self._current_process = None
                return "⏹️ 音乐已停止"
            return "当前没有播放"

        if action == "play" and query:
            # 0. Init
            file_ext = "mp3"
            mp3_url = None
            song_name = ""
            artist = ""
            source_type = "itunes"
            file_path = None
            
            # --- 1. Try Netease First (via pyncm - no cookie needed!) ---
            print(f"☁️ Searching Netease Music for: {query}...")
            song_data = self._search_netease(query, None)
            
            if song_data:
                song_id = song_data['id']
                url = self._get_netease_url(song_id, None)
                success = False
                
                # Method A: pyncm URL (most reliable)
                if url:
                    print(f"   Verifying Netease Stream...")
                    temp_path = os.path.join(self._cache_dir, f"netease_{song_id}.mp3")
                    if self._download_file(url, temp_path, None):
                        mp3_url = url
                        file_path = temp_path
                        success = True
                
                # Method B: Outchain (Fallback)
                if not success:
                    print("⚠️ Method A failed. Trying Netease 'Outchain' (Method B)...")
                    url_b = f"http://music.163.com/song/media/outer/url?id={song_id}.mp3"
                    temp_path_b = os.path.join(self._cache_dir, f"netease_out_{song_id}.mp3")
                    if self._download_file(url_b, temp_path_b, None):
                        mp3_url = url_b
                        file_path = temp_path_b
                        success = True
                        print("✅ Netease 'Outchain' method worked!")

                if success:
                    source_type = "netease"
                    song_name = song_data['name']
                    artist = song_data['artists'][0]['name']
                else:
                    print("⚠️ All Netease methods failed. Falling back.")

            # --- 2. Try YouTube (Unlimited Library) ---
            if not mp3_url: 
                print(f"🌍 Searching YouTube (Unlimited) for: {query}...")
                yt_data = self._search_youtube(query)
                if yt_data:
                    source_type = "youtube"
                    song_name = yt_data['name']
                    artist = "YouTube"
                    file_path = yt_data['path']
                    mp3_url = "LOCAL_FILE" # Already downloaded
                    print("✅ YouTube Download Success!")
            
            # --- 3. Fallback to iTunes (Reliable Preview) ---
            if not mp3_url:
                print(f"☁️ Searching Apple Music (Preview) for: {query}...")
                song_data = self._search_itunes(query)
                if song_data:
                    source_type = "itunes"
                    song_name = song_data.get('trackName')
                    artist = song_data.get('artistName')
                    mp3_url = song_data.get('previewUrl')
                    file_ext = "m4a"
                    
                    # Clean title for filename
                    clean_name = f"{song_name}-{artist}".replace("/", "_")
                    file_path = os.path.join(self._cache_dir, f"{clean_name}.{file_ext}")
                    
                    # Download iTunes
                    if not self._download_file(mp3_url, file_path):
                         return f"❌ 下载失败: {song_name}"
                
            if not mp3_url:
                return f"❌ 未找到歌曲或播放链接: {query}"

            # 4. Play
            if self._current_process:
                self._current_process.terminate()
            
            try:
                cmd = self._get_player_command(file_path)
                self._current_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                title_prefix = f"🌟({source_type.upper()})" 
                return f"▶️ {title_prefix} 正在播放: {song_name} - {artist}"
            except Exception as e:
                return f"❌ 播放器错误: {e}"
                
        return "❌ 请提供歌名"

    def _get_player_command(self, file_path):
        import platform
        sys_name = platform.system()
        if sys_name == "Darwin":
            return ["afplay", file_path]
        elif sys_name == "Linux":
            return ["mpg123", file_path]
        else:
            return ["ffplay", "-nodisp", "-autoexit", file_path]

    def _search_youtube(self, keyword):
        """Search and Download via YouTube (Unlimited)"""
        try:
            safe_name = keyword.replace("/", "_").replace(" ", "_")
            # Try to grab m4a (no ffmpeg needed usually) or best audio
            # Note: macOS afplay plays m4a. Linux need ffplay/mpv for m4a or ffmpeg to convert.
            file_path = os.path.join(self._cache_dir, f"yt_{safe_name}.m4a") 
            
            if os.path.exists(file_path) and os.path.getsize(file_path) > 100*1024:
                return {"path": file_path, "name": keyword}

            print(f"   running yt-dlp query: {keyword}")
            
            # Check for YouTube Cookie
            yt_cookie = os.environ.get("YOUTUBE_COOKIE_PATH") # Path to cookies.txt
            
            cmd = [
                "python3", "-m", "yt_dlp",
                f"ytsearch1:{keyword} audio",
                "-f", "bestaudio[ext=m4a]/bestaudio", # Get m4a directly to avoid ffmpeg re-encode if possible
                "--output", file_path,
                "--no-playlist",
                "--max-downloads", "1"
            ]
            
            if yt_cookie and os.path.exists(yt_cookie):
                cmd.extend(["--cookies", yt_cookie])
            
            # Run
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"⚠️ YouTube DL Failed: {result.stderr[:200]}")
                if "Sign in" in result.stderr:
                    print("   (Need YOUTUBE_COOKIE_PATH env var to bypass Bot Check)")
                return None
            
            if os.path.exists(file_path) and os.path.getsize(file_path) > 10*1024:
                 return {"path": file_path, "name": keyword}
                 
        except Exception as e:
            print(f"YouTube Download Error: {e}")
        return None

    def _search_itunes(self, keyword):
        url = "https://itunes.apple.com/search"
        params = {"term": keyword, "media": "music", "limit": 1, "country": "CN"}
        try:
            r = requests.get(url, params=params, timeout=10)
            data = r.json()
            if data['resultCount'] > 0:
                return data['results'][0]
        except Exception:
            pass
        return None

    def _search_netease(self, keyword, cookie):
        """Search Netease via pyncm (bypasses all anti-bot)"""
        try:
            from pyncm import apis
            result = apis.cloudsearch.GetSearchResult(keyword, limit=1)
            if result['code'] == 200 and result['result']['songs']:
                song = result['result']['songs'][0]
                # Convert to compatible format
                return {
                    'id': song['id'],
                    'name': song['name'],
                    'artists': [{'name': song['ar'][0]['name']}]
                }
        except Exception as e:
            print(f"pyncm Search Error: {e}")
        return None

    def _get_netease_url(self, song_id, cookie):
        """Get playable URL via pyncm"""
        try:
            from pyncm import apis
            result = apis.track.GetTrackAudio(song_id, bitrate=320000)
            if result['code'] == 200 and result['data']:
                return result['data'][0]['url']
        except Exception as e:
            print(f"pyncm URL Error: {e}")
        return None

    def _download_file(self, url, path, cookie=None):
        if os.path.exists(path) and os.path.getsize(path) > 100 * 1024:
            try:
                with open(path, 'rb') as f:
                    header = f.read(500)
                    if b'<!doctype html' in header.lower() or b'<html' in header.lower() or b'{"msg":' in header:
                        print(f"🗑️ Found corrupted/HTML cache ({os.path.basename(path)}). Deleting.")
                        os.remove(path)
                    else:
                        return True
            except:
                pass
        
        try:
            print(f"   Source URL: {url}")
            cmd = [
                "curl", "-L", "-o", path,
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "--referer", "http://music.163.com/",
                "--header", "Range: bytes=0-",
                "--max-time", "30",
                url
            ]
            if cookie:
                cmd.extend(["--cookie", cookie])
                
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if os.path.exists(path) and os.path.getsize(path) > 10 * 1024:
                 try:
                    with open(path, 'rb') as f:
                        header = f.read(500)
                        if b'<!doctype html' in header.lower() or b'<html' in header.lower():
                            print("❌ Downloaded file is HTML (Fake/Blocked file).")
                            os.remove(path)
                            return False
                 except: pass
                 return True
            else:
                print("❌ File too small - Real download failure")
                if os.path.exists(path): os.remove(path)
                return False
        except Exception as e:
            print(f"DEBUG: Download Error: {e}")
        return False

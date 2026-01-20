"""
Jarvis System Verification Suite
Runs a complete health check on hardware, network, and software components.
"""
import sys
import os
import asyncio
import socket
import json
import gzip
import time

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def print_status(component, status, message=""):
    color = GREEN if status == "OK" else RED
    if status == "WARN": color = YELLOW
    print(f"{component:<25} [{color}{status}{RESET}] {message}")

async def verify_network():
    print("\n🌐 Network Connectivity")
    try:
        host = "openspeech.bytedance.com"
        port = 443
        socket.create_connection((host, port), timeout=3)
        print_status("Volcengine API", "OK", f"Connected to {host}:443")
        return True
    except OSError:
        print_status("Volcengine API", "FAIL", "Cannot reach server")
        return False

def verify_audio():
    print("\n🎙️ Audio Hardware")
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        
        # Check Input
        input_devs = 0
        default_input = None
        try:
            default_input = p.get_default_input_device_info()
        except:
            pass
            
        # Check Output
        output_devs = 0
        default_output = None
        try:
            default_output = p.get_default_output_device_info()
        except:
            pass

        for i in range(p.get_device_count()):
            dev = p.get_device_info_by_index(i)
            if dev['maxInputChannels'] > 0: input_devs += 1
            if dev['maxOutputChannels'] > 0: output_devs += 1
        
        if default_input:
            print_status("Microphone", "OK", f"Default: {default_input['name']}")
        else:
            print_status("Microphone", "FAIL", "No default input device found")
            
        if default_output:
            print_status("Speaker", "OK", f"Default: {default_output['name']}")
        else:
            print_status("Speaker", "FAIL", "No default output device found")
            
        p.terminate()
        return bool(default_input and default_output)
    except ImportError:
        print_status("PyAudio", "FAIL", "Library not installed")
        return False
    except Exception as e:
        print_status("Audio Check", "FAIL", str(e))
        return False

async def verify_doubao_handshake():
    print("\n🤝 Doubao API Authentication")
    try:
        import websockets
        import ssl
        from jarvis_doubao_config import ws_connect_config, start_session_req
        from jarvis_doubao_realtime import DoubaoProtocol
        
        headers = ws_connect_config["headers"]
        ws_url = ws_connect_config["base_url"]
        
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        
        async with websockets.connect(ws_url, additional_headers=headers, ssl=ssl_ctx) as ws:
            # Send Start Connection
            req = bytearray(DoubaoProtocol.generate_header())
            req.extend((1).to_bytes(4, 'big'))
            payload = gzip.compress(b"{}")
            req.extend(len(payload).to_bytes(4, 'big'))
            req.extend(payload)
            
            await ws.send(req)
            resp = await ws.recv()
            
            # Simple check of response
            if len(resp) > 4:
                print_status("Protocol Handshake", "OK", "Server responded")
                return True
            else:
                print_status("Protocol Handshake", "FAIL", "Empty response")
                return False
                
    except Exception as e:
        print_status("API Verification", "FAIL", str(e))
        return False

def verify_dependencies():
    print("\n📦 Dependencies")
    deps = ["websockets", "pyaudio", "aiohttp", "requests", "psutil", "miio"]
    all_ok = True
    for dep in deps:
        try:
            __import__(dep)
            if dep == "miio":
                print_status("python-miio", "OK", "Installed")
            else:
                print_status(dep, "OK", "Installed")
        except ImportError:
            print_status(dep, "FAIL", "Not installed")
            all_ok = False
    return all_ok

async def main():
    print("========================================")
    print("   JARVIS SYSTEM DIAGNOSTIC TOOL        ")
    print("========================================")
    
    checks = []
    checks.append(verify_dependencies())
    checks.append(await verify_network())
    checks.append(verify_audio())
    checks.append(await verify_doubao_handshake())
    
    print("\n========================================")
    if all(checks):
        print(f"{GREEN}✅ SYSTEM READY. RUN 'python3 hybrid_jarvis.py' TO START.{RESET}")
    else:
        print(f"{RED}❌ SYSTEM ISSUES DETECTED. PLEASE FIX ABOVE ERRORS.{RESET}")

if __name__ == "__main__":
    asyncio.run(main())

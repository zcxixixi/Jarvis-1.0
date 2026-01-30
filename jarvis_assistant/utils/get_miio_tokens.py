#!/usr/bin/env python3
"""
Xiaomi Cloud Token Extractor
Helps user get IP and Token for their devices.
"""
import sys
import asyncio
import os
import json
from getpass import getpass

try:
    from micloud import MiCloud
except ImportError:
    print("❌ Library 'micloud' not found.")
    print("👉 Please run: pip install micloud")
    sys.exit(1)

def main():
    print("========================================")
    print("🏠 Xiaomi Cloud Token Extractor")
    print("========================================")
    print("This script will connect to Xiaomi Cloud to fetch your device tokens.")
    print("These tokens are required for Jarvis to control your devices.")
    print("")
    
    username = input("Enter Xiaomi Cloud Username (Email/Phone): ").strip()
    password = getpass("Enter Xiaomi Cloud Password: ").strip()
    
    if not username or not password:
        print("❌ Username and password are required.")
        return

    print("\n🔄 Logging in to Xiaomi Cloud...")
    mc = MiCloud(username, password)
    
    try:
        success = mc.login()
        if not success:
            print("❌ Login failed. Please check credentials.")
            return
    except Exception as e:
        print(f"❌ Login Error: {e}")
        return

    print("✅ Login successful!")
    print("\n🔄 Fetching devices...")
    
    try:
        devices = mc.get_devices()
        print(f"\n📦 Found {len(devices)} devices:")
        print("-" * 60)
        print(f"{'Name':<20} | {'IP':<15} | {'Token':<32} | {'Model'}")
        print("-" * 60)
        
        found_devices = []
        for d in devices:
            name = d.get('name', 'Unknown')
            ip = d.get('localip', 'N/A')
            token = d.get('token', 'N/A')
            model = d.get('model', 'N/A')
            
            print(f"{name:<20} | {ip:<15} | {token:<32} | {model}")
            
            if ip != 'N/A' and token != 'N/A':
                found_devices.append((name, ip, token, model))
                
        print("-" * 60)
        
        if found_devices:
            print("\n📝 Recommended Configuration (Add to .env or config):")
            print("MI_DEVICES='{")
            device_map = {}
            for name, ip, token, model in found_devices:
                # Create a simple key from name
                key = name.lower().replace(" ", "_")
                device_map[key] = {"ip": ip, "token": token, "model": model}
                print(f'  "{key}": {{"ip": "{ip}", "token": "{token}", "model": "{model}"}},')
            print("}'")
            
            # Save to a file for convenience
            with open("xiaomi_devices.json", "w") as f:
                json.dump(device_map, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Saved to 'xiaomi_devices.json'")
            
    except Exception as e:
        print(f"❌ Error fetching devices: {e}")

if __name__ == "__main__":
    main()

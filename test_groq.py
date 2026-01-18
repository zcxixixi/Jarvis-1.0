
import os
from config import Config
from groq import Groq

def test_groq():
    api_key = Config.GROQ_API_KEY
    if not api_key:
        print("❌ 错误: .env文件中未找到 GROQ_API_KEY")
        return

    print(f"🔑 当前 API Key: {api_key[:5]}...{api_key[-4:]}")
    print("🚀 正在尝试连接 Groq API...")
    
    try:
        client = Groq(api_key=api_key)
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": "Hello, are you working?",
                }
            ],
            model="llama-3.3-70b-versatile",
        )
        print("✅ 连接成功！")
        print(f"🤖 回复: {chat_completion.choices[0].message.content}")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        print("\n💡 提示: 如果您在中国，Groq 需要全局代理/VPN 才能访问。")

if __name__ == "__main__":
    test_groq()

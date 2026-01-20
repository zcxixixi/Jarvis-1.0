#!/usr/bin/env python3
"""
JARVIS CLI Interface for Mac
Text-based interface for development and testing
"""
import sys
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from jarvis_core import JarvisCore
from config import Config

console = Console()

def print_banner():
    """Print JARVIS banner"""
    banner = """
    ╔═══════════════════════════════════════╗
    ║                                       ║
    ║      🤖  J.A.R.V.I.S  AI Assistant  ║
    ║                                       ║
    ║   Just A Rather Very Intelligent     ║
    ║           System                      ║
    ║                                       ║
    ╚═══════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")
    console.print("✨ 为您服务，先生。输入 'exit' 或 'quit' 退出\n", style="italic")

def main():
    """Main CLI loop"""
    try:
        # Initialize JARVIS
        console.print("🔧 正在初始化贾维斯...", style="yellow")
        jarvis = JarvisCore()
        
        # Register All Tools (Skills)
        try:
            from tools import get_all_tools
            tools = get_all_tools()
            for tool in tools:
                jarvis.register_tool(tool)
            console.print(f"🔧 已加载 {len(tools)} 个技能", style="green")
            if Config.DEBUG:
                for tool in tools:
                    console.print(f"   • {tool.name}: {tool.description[:30]}...")
        except Exception as e:
            console.print(f"⚠️ 技能加载失败: {e}", style="yellow")
            if Config.DEBUG:
                import traceback
                console.print(traceback.format_exc(), style="dim red")
            
        console.print("✅ 贾维斯已就绪！\n", style="green")
        
        # Print banner
        print_banner()
        
        # Main conversation loop
        while True:
            try:
                # Get user input
                user_input = Prompt.ask("\n[bold blue]您[/bold blue]")
                
                # Check for exit commands
                if user_input.lower() in ['exit', 'quit', '退出', 'bye']:
                    console.print("\n👋 再见，先生。随时为您服务。", style="cyan italic")
                    break
                
                # Check for special commands
                if user_input.lower() in ['clear', '清空']:
                    jarvis.clear_history()
                    console.print("🧹 对话历史已清空", style="yellow")
                    continue
                
                if user_input.lower() in ['stats', '统计']:
                    stats = jarvis.get_stats()
                    console.print(f"\n📊 统计信息:", style="cyan")
                    console.print(f"   消息数: {stats['messages']}")
                    console.print(f"   工具数: {stats['tools']}")
                    continue
                
                # Skip empty input
                if not user_input.strip():
                    continue
                
                # Show thinking indicator
                console.print("💭 贾维斯正在思考...", style="dim")
                
                # Get response from JARVIS
                response = jarvis.chat(user_input)
                
                # Display response in a panel
                console.print("\n[bold cyan]贾维斯[/bold cyan]:")
                console.print(Panel(
                    Markdown(response),
                    border_style="cyan",
                    padding=(1, 2)
                ))
                
            except KeyboardInterrupt:
                console.print("\n\n👋 再见，先生。", style="cyan italic")
                break
            except EOFError:
                console.print("\n\n👋 检测到输入结束，再见先生。", style="cyan italic")
                break
            except Exception as e:
                console.print(f"\n❌ 错误: {e}", style="red")
                if Config.DEBUG:
                    import traceback
                    console.print(traceback.format_exc(), style="dim red")
    
    except ValueError as e:
        # Configuration error
        console.print(f"\n❌ 配置错误: {e}", style="red bold")
        console.print("\n💡 请按以下步骤配置：", style="yellow")
        console.print("   1. 复制 .env.example 到 .env")
        console.print("   2. 在 .env 中设置你的 GROK_API_KEY")
        console.print("   3. 重新运行此程序\n")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n❌ 初始化失败: {e}", style="red bold")
        if Config.DEBUG:
            import traceback
            console.print(traceback.format_exc(), style="dim red")
        sys.exit(1)

if __name__ == "__main__":
    main()

"""
Plugin Manager for Jarvis Universal Agent
Enables dynamic tool discovery and loading
"""

import os
import importlib
import inspect
from pathlib import Path
from typing import List, Dict, Any, Type
from jarvis_assistant.services.tools.base import BaseTool


class PluginManager:
    """Manages dynamic loading of tools/plugins"""
    
    def __init__(self, tools_dir: str = "tools"):
        # Detect absolute path relative to this file
        # utils/../services/tools
        base_dir = Path(__file__).parent.parent 
        self.tools_dir = base_dir / "services" / tools_dir
        self.loaded_plugins: Dict[str, BaseTool] = {}
        self.plugin_metadata: Dict[str, Dict[str, Any]] = {}
    
    def discover_plugins(self) -> List[str]:
        """
        Auto-discover all tool files in the tools directory
        
        Returns:
            List of discovered plugin module names
        """
        if not self.tools_dir.exists():
            print(f"⚠️ Tools directory not found: {self.tools_dir}")
            return []
        
        plugins = []
        for file in self.tools_dir.glob("*_tools.py"):
            if file.name == "__init__.py" or file.name == "base.py":
                continue
            module_name = file.stem  # filename without extension
            plugins.append(module_name)
        
        print(f"📦 Discovered {len(plugins)} plugin modules")
        return plugins
    
    def load_plugin(self, module_name: str) -> List[BaseTool]:
        """
        Load a single plugin module and extract all tools
        
        Args:
            module_name: Name of the module (e.g., "weather_tools")
        
        Returns:
            List of instantiated tool objects
        """
        try:
            # Import the module
            module = importlib.import_module(f"jarvis_assistant.services.tools.{module_name}")
            
            # Find all classes that inherit from BaseTool
            tools = []
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, BaseTool) and obj != BaseTool:
                    try:
                        tool_instance = obj()
                        tools.append(tool_instance)
                        self.loaded_plugins[tool_instance.name] = tool_instance
                        self.plugin_metadata[tool_instance.name] = {
                            "module": module_name,
                            "class": name,
                            "description": tool_instance.description
                        }
                    except Exception as e:
                        print(f"    ⚠️ Failed to instantiate {name}: {e}")
            
            if tools:
                print(f"  ✅ {module_name}: loaded {len(tools)} tools")
            
            return tools
            
        except Exception as e:
            print(f"  ❌ Failed to load {module_name}: {e}")
            return []
    
    def load_all_plugins(self) -> Dict[str, BaseTool]:
        """
        Discover and load all available plugins
        
        Returns:
            Dictionary mapping tool names to tool instances
        """
        print("🔌 Loading all plugins...")
        
        plugin_modules = self.discover_plugins()
        
        for module_name in plugin_modules:
            self.load_plugin(module_name)
        
        print(f"✅ Loaded {len(self.loaded_plugins)} total tools")
        return self.loaded_plugins
    
    def reload_plugin(self, module_name: str) -> List[BaseTool]:
        """
        Hot reload a plugin module (useful for development)
        
        Args:
            module_name: Name of the module to reload
        
        Returns:
            List of reloaded tool instances
        """
        print(f"🔄 Reloading {module_name}...")
        
        # Remove old instances
        old_tools = [
            name for name, meta in self.plugin_metadata.items()
            if meta["module"] == module_name
        ]
        for tool_name in old_tools:
            del self.loaded_plugins[tool_name]
            del self.plugin_metadata[tool_name]
        
        # Reload module
        try:
            module = importlib.import_module(f"jarvis_assistant.services.tools.{module_name}")
            importlib.reload(module)
        except Exception as e:
            print(f"❌ Reload failed: {e}")
            return []
        
        # Load new versions
        return self.load_plugin(module_name)
    
    def get_plugin_info(self, tool_name: str) -> Dict[str, Any]:
        """Get metadata about a specific tool"""
        return self.plugin_metadata.get(tool_name, {})
    
    def list_plugins(self) -> None:
        """Print all loaded plugins"""
        print(f"\n📋 Loaded Plugins ({len(self.loaded_plugins)}):")
        print("-" * 60)
        
        # Group by module
        by_module: Dict[str, List[str]] = {}
        for tool_name, meta in self.plugin_metadata.items():
            module = meta["module"]
            if module not in by_module:
                by_module[module] = []
            by_module[module].append(tool_name)
        
        for module, tools in sorted(by_module.items()):
            print(f"  {module}:")
            for tool in sorted(tools):
                desc = self.plugin_metadata[tool]["description"]
                print(f"    - {tool}: {desc[:50]}...")


# Global plugin manager instance
_plugin_manager = None


def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager instance"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
        _plugin_manager.load_all_plugins()
    return _plugin_manager


# Quick test
if __name__ == "__main__":
    manager = PluginManager()
    plugins = manager.load_all_plugins()
    manager.list_plugins()
    
    print(f"\n✅ Successfully loaded {len(plugins)} tools")

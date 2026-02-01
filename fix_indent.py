# 临时修复脚本 - 手动修复 query_router.py 的缩进问题

import re

file_path = "/Users/kaijimima1234/Desktop/jarvis/jarvis_assistant/core/query_router.py"

with open(file_path, 'r') as f:
    lines = f.readlines()

# 找到问题区域（大约 line 125-170）并修复缩进
# 关键：所有在 async with block 内的代码都需要16个空格缩进

fixed_lines = []
in_problem_zone = False
for i, line in enumerate(lines, 1):
    # 检测问题开始（async with self._processing_lock）
    if 'async with self._processing_lock:' in line:
        in_problem_zone = True
        fixed_lines.append(line)
        continue
    
    # 检测问题结束（except 或 finally）
    if in_problem_zone and ('except Exception as e:' in line or 'finally:' in line):
        # 恢复到12空格
        if line.startswith('        '):  # 已经是8空格
            fixed_lines.append('            ' + line.lstrip())  # 改成12空格
        else:
            fixed_lines.append(line)
        in_problem_zone = False
        continue
    
    # 在问题区域内，确保正确缩进
    if in_problem_zone:
        # 移除所有前导空格
        stripped = line.lstrip()
        if stripped:  # 非空行
            # 确定正确的缩进级别
            if stripped.startswith('try:'):
                fixed_lines.append('                ' + stripped)  # 16空格
            elif stripped.startswith('#') or stripped.startswith('resolved') or stripped.startswith('t') or stripped.startswith('if') or stripped.startswith('intent') or stripped.startswith('print') or stripped.startswith('logger') or stripped.startswith('self.') or stripped.startswith('total') or stripped.startswith('classify') or stripped.startswith('context') or stripped.startswith('await'):
                fixed_lines.append('                ' + stripped)  # 16空格
            else:
                fixed_lines.append(line)  # 保持原样
        else:
            fixed_lines.append(line)  # 空行保持
        continue
    
    # 其他行保持不变
    fixed_lines.append(line)

# 写回文件
with open(file_path, 'w') as f:
    f.writelines(fixed_lines)

print("✅ 缩进已修复")

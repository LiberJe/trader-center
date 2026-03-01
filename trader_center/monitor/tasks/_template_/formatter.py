"""任务专用格式化器"""

from typing import Dict, Any


def format_report(result: Dict[str, Any]) -> str:
    """格式化报告"""
    return f"""
========================================
任务执行报告
========================================
状态: {result.get('status')}
日期: {result.get('date')}
消息: {result.get('message')}
========================================
"""


def export_to_file(result: Dict[str, Any], filepath: str) -> None:
    """导出到文件"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(format_report(result))

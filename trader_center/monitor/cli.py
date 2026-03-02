#!/usr/bin/env python3
"""
Monitor CLI - 通用任务执行命令行工具

Usage:
    python -m trader_center.monitor --list
    python -m trader_center.monitor fund_flow
    python -m trader_center.monitor fund_flow --date 2025-08-26
    python -m trader_center.monitor fund_flow -o report.txt
"""

import argparse
import sys
from datetime import date, datetime
from typing import Optional


class DateParseError(Exception):
    """日期解析错误"""
    pass


def format_value(value: float) -> str:
    """格式化数值显示（资金、百分比等）

    Args:
        value: 数值

    Returns:
        格式化后的字符串，自动选择亿/万/元单位
    """
    if abs(value) >= 1e8:
        return f"{value/1e8:+.2f}亿"
    elif abs(value) >= 1e4:
        return f"{value/1e4:+.2f}万"
    else:
        return f"{value:+.2f}"


def parse_date(date_str: Optional[str]) -> date:
    """解析日期字符串

    Args:
        date_str: 日期字符串，支持 YYYY-MM-DD 或 YYYYMMDD

    Returns:
        date 对象

    Raises:
        DateParseError: 日期格式无效
    """
    if date_str is None:
        return date.today()

    try:
        return date.fromisoformat(date_str)
    except ValueError:
        try:
            return datetime.strptime(date_str, "%Y%m%d").date()
        except ValueError:
            raise DateParseError(
                f"Invalid date format: {date_str}. Use YYYY-MM-DD or YYYYMMDD"
            )


def print_task_list(router):
    """打印任务列表"""
    print("\n可用任务列表:")
    print("-" * 50)

    tasks = router.list_tasks()
    if not tasks:
        print("  (暂无任务)")
        return

    # 按 category 分组
    by_category = {}
    for task_name in tasks:
        info = router.get_task_info(task_name)
        cat = info.get('category', 'default') if info else 'default'
        by_category.setdefault(cat, []).append((task_name, info))

    for category, items in sorted(by_category.items()):
        print(f"\n  [{category}]")
        for task_name, info in sorted(items):
            desc = info.get('description', '') if info else ''
            print(f"    {task_name:<20} {desc}")

    print()


def print_result(result: dict, task_name: str, args):
    """打印任务执行结果

    Args:
        result: 任务返回的结果字典
        task_name: 任务名称
        args: 命令行参数
    """
    status = result.get('status', 'unknown')

    if status == 'skipped':
        reason = result.get('reason', '未知原因')
        target_date = result.get('date', 'N/A')
        print(f"\n[SKIP]  {target_date} 任务跳过")
        print(f"   原因: {reason}")
        return

    if status == 'error':
        reason = result.get('reason', '未知错误')
        print(f"\n[ERR] 任务执行失败: {reason}", file=sys.stderr)
        return

    if status != 'success':
        print(f"\n[ERR] 未知的任务状态: {status}", file=sys.stderr)
        return

    # 成功状态，使用任务的格式化器输出
    from trader_center.monitor.task_router import get_task_router

    router = get_task_router()
    task_class = router.get_task(task_name)

    if task_class:
        task = task_class()
        output = task.format_output(result, top_n=args.top)
        print(output)
    else:
        # 回退：直接打印结果
        print(f"\n[OK] 任务执行成功")
        for key, value in result.items():
            if key != 'status':
                print(f"  {key}: {value}")


def export_result(result: dict, filepath: str, task_name: str):
    """导出结果到文件

    优先使用任务特定的导出方式，否则使用通用格式。
    """
    try:
        # 尝试使用任务特定的导出
        if task_name == 'fund_flow':
            from trader_center.monitor.tasks.fund_flow import export_to_file
            export_to_file(result, filepath)
            return
    except Exception:
        pass

    # 通用导出
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"任务报告 - {task_name} - {result.get('date', 'N/A')}\n")
        f.write(f"{'='*60}\n\n")
        f.write(f"状态: {result.get('status', 'unknown')}\n\n")

        for key, value in result.items():
            if key not in ('status', 'date'):
                f.write(f"{key}:\n{value}\n\n")

    print(f"\n[OK] 报告已导出到: {filepath}")


def clean_data(target_date: Optional[date], data_type: str, all_dates: bool = False) -> dict:
    """清理资金流向数据

    Args:
        target_date: 目标日期（当 all_dates=True 时忽略）
        data_type: 数据类型 - "all" | "market" | "stock" | "sector"
        all_dates: 是否清理所有日期的数据

    Returns:
        删除结果统计字典
    """
    import trader_center.data_hub as dh

    # 清理内存缓存
    dh.clear_cache()

    if all_dates:
        # 删除所有日期的数据
        result = dh.delete_all_fund_flow_data(
            data_type=data_type,
            clear_cache=True,
        )
    else:
        # 删除指定日期的数据
        result = dh.delete_fund_flow_data(
            target_date=target_date,
            data_type=data_type,
            clear_cache=True,
        )

    return result


def print_clean_result(result: dict, target_date: Optional[date], data_type: str, all_dates: bool = False):
    """打印清理结果

    Args:
        result: 删除结果统计
        target_date: 目标日期
        data_type: 数据类型
        all_dates: 是否清理了所有日期的数据
    """
    type_names = {
        "all": "所有",
        "market": "大盘",
        "stock": "个股",
        "sector": "板块",
    }

    if all_dates:
        print(f"\n[INFO] 清理所有日期的{type_names.get(data_type, data_type)}资金流向数据")
    else:
        print(f"\n[INFO] 清理 {target_date} 的{type_names.get(data_type, data_type)}资金流向数据")
    print("[OK] 已删除:")
    print(f"     大盘资金流向: {result.get('market', 0)} 条")
    print(f"     个股资金流向: {result.get('stock', 0)} 条")
    print(f"     板块资金流向: {result.get('sector', 0)} 条")


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="Monitor - A股市场观察任务执行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --list                     # 列出所有可用任务
  %(prog)s fund_flow                  # 执行资金流向任务
  %(prog)s fund_flow -d 2025-08-26    # 执行指定日期
  %(prog)s fund_flow -t 20            # 显示前20条
  %(prog)s fund_flow -o report.txt    # 导出到文件
  %(prog)s clean -d 2025-08-26        # 清理指定日期数据
  %(prog)s clean -d 2025-08-26 -t market  # 只清理大盘数据
  %(prog)s clean --all                # 清理所有日期数据
  %(prog)s clean --all --type stock   # 清理所有日期的个股数据
        """
    )

    parser.add_argument(
        'task',
        nargs='?',
        help='要执行的任务名称'
    )

    parser.add_argument(
        '-l', '--list',
        action='store_true',
        help='列出所有可用任务'
    )

    parser.add_argument(
        '-d', '--date',
        type=str,
        default=None,
        help='目标日期 (YYYY-MM-DD 或 YYYYMMDD)，默认为今日'
    )

    parser.add_argument(
        '-t', '--top',
        type=int,
        default=10,
        help='显示前N条记录 (默认: 10)'
    )

    parser.add_argument(
        '-o', '--output',
        type=str,
        default=None,
        help='导出结果到文件'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细输出'
    )

    parser.add_argument(
        '--type',
        type=str,
        default='all',
        choices=['all', 'market', 'stock', 'sector'],
        help='数据类型 (仅用于 clean 命令): all(默认), market, stock, sector'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        dest='all_dates',
        help='清理所有日期的数据（用于 clean 命令）'
    )

    args = parser.parse_args()

    # 导入路由器
    try:
        from trader_center.monitor.task_router import get_task_router
        router = get_task_router()
    except ImportError as e:
        print(f"[ERR] 导入错误: {e}", file=sys.stderr)
        sys.exit(1)

    # 列出任务
    if args.list:
        print_task_list(router)
        sys.exit(0)

    # 检查任务名称
    if not args.task:
        print("[ERR] 请指定任务名称或使用 --list 查看可用任务", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    # 处理 clean 命令
    if args.task == 'clean':
        # 检查参数：必须指定 --date 或 --all 之一
        if not args.date and not args.all_dates:
            print("[ERR] 错误: 请指定 --date 或 --all 参数", file=sys.stderr)
            sys.exit(1)

        if args.all_dates:
            # 清理所有日期
            if args.verbose:
                print(f"[INFO] 清理所有日期的数据，类型: {args.type}")

            try:
                result = clean_data(None, args.type, all_dates=True)
                print_clean_result(result, None, args.type, all_dates=True)
            except Exception as e:
                print(f"[ERR] 清理数据异常: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            # 清理指定日期
            try:
                target_date = parse_date(args.date)
            except DateParseError as e:
                print(f"[ERR] 错误: {e}", file=sys.stderr)
                sys.exit(1)

            if args.verbose:
                print(f"[INFO] 清理数据: {target_date}, 类型: {args.type}")

            try:
                result = clean_data(target_date, args.type, all_dates=False)
                print_clean_result(result, target_date, args.type, all_dates=False)
            except Exception as e:
                print(f"[ERR] 清理数据异常: {e}", file=sys.stderr)
                sys.exit(1)

        sys.exit(0)

    # 检查任务是否存在
    task_info = router.get_task_info(args.task)
    if task_info is None:
        available = router.list_tasks()
        print(f"[ERR] 未知任务: '{args.task}'", file=sys.stderr)
        if available:
            print(f"可用任务: {', '.join(available)}", file=sys.stderr)
        else:
            print("当前没有可用任务", file=sys.stderr)
        sys.exit(1)

    # 解析日期
    try:
        target_date = parse_date(args.date)
    except DateParseError as e:
        print(f"[ERR] 错误: {e}", file=sys.stderr)
        sys.exit(1)

    # 执行任务
    if args.verbose:
        print(f"[INFO] 执行任务: {args.task}")
        print(f"[INFO] 目标日期: {target_date}")

    try:
        result = router.execute(args.task, target_date=target_date)
    except Exception as e:
        print(f"[ERR] 任务执行异常: {e}", file=sys.stderr)
        sys.exit(1)

    # 输出结果
    print_result(result, args.task, args)

    # 导出到文件
    if args.output:
        export_result(result, args.output, args.task)

    # 根据状态返回退出码
    if result.get('status') == 'error':
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()

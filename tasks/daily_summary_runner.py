"""
每日任务汇总 Runner

读取 task_config.yaml 中配置的子任务，逐一执行并汇总结论到 daily_summary.md。

Usage:
    python tasks/daily_summary_runner.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import io
import importlib.util
from contextlib import redirect_stdout
from datetime import date, datetime

import json


def load_task_config(config_path: Path) -> dict:
    """读取任务配置文件"""
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def import_runner_module(script_name: str, tasks_dir: Path):
    """动态导入 runner 模块"""
    script_path = tasks_dir / script_name
    module_name = script_name.replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def run_task(task: dict, tasks_dir: Path) -> dict:
    """执行单个任务，返回结果字典"""
    name = task["name"]
    script = task["script"]
    description = task.get("description", "")

    print(f"\n{'='*60}")
    print(f"执行任务: {name} ({description})")
    print(f"{'='*60}")

    try:
        module = import_runner_module(script, tasks_dir)
        if not hasattr(module, "main"):
            return {
                "name": name,
                "description": description,
                "status": "error",
                "error": f"脚本 {script} 中没有 main() 函数",
            }

        # 捕获 runner 的输出，避免污染控制台
        captured = io.StringIO()
        with redirect_stdout(captured):
            result = module.main(report_subdir=name)

        if result is None:
            return {
                "name": name,
                "description": description,
                "status": "error",
                "error": "runner.main() 未返回结果",
            }

        return {
            "name": name,
            "description": description,
            "status": result.get("status", "unknown"),
            "error_message": result.get("error_message", ""),
            "metrics": result.get("metrics", {}),
            "holdings_summary": result.get("holdings_summary", ""),
            "signals_summary": result.get("signals_summary", ""),
            "report_path": result.get("report_path", ""),
        }

    except Exception as e:
        return {
            "name": name,
            "description": description,
            "status": "error",
            "error": str(e),
        }


def generate_summary_report(results: list, report_dir: Path, today_display: str):
    """生成汇总报告 daily_summary.md"""

    report = f"# 每日任务汇总报告 - {today_display}\n\n"

    # 执行概览
    report += "## 执行概览\n\n"
    report += "| 任务 | 描述 | 状态 |\n"
    report += "|------|------|------|\n"

    for r in results:
        status_icon = "成功" if r["status"] == "success" else ("失败" if r["status"] == "error" else r["status"])
        report += f"| {r['name']} | {r.get('description', '')} | {status_icon} |\n"

    report += "\n---\n"

    # 每个任务的详情
    for r in results:
        report += f"\n## {r.get('description', r['name'])}\n\n"

        if r["status"] != "success":
            error_msg = r.get("error_message", "") or r.get("error", "未知错误")
            report += f"> 执行失败: {error_msg}\n\n"
            continue

        metrics = r.get("metrics", {})
        report += "| 指标 | 数值 |\n"
        report += "|------|------|\n"
        report += f"| 累计收益率 | {metrics.get('return_pct', 0):+.2%} |\n"
        report += f"| 最大回撤 | {metrics.get('max_drawdown', 0):.2%} |\n"
        report += f"| 夏普比率 | {metrics.get('sharpe_ratio', 0):.2f} |\n"
        report += f"| 当前总资产 | {metrics.get('final_value', 0):,.2f} 元 |\n"
        report += f"| 总交易次数 | {metrics.get('total_trades', 0)} |\n"
        report += f"| 胜率 | {metrics.get('win_rate', 0):.1%} |\n"

        holdings = r.get("holdings_summary", "")
        if holdings:
            report += f"\n**当前持仓**: {holdings}\n"

        signals = r.get("signals_summary", "")
        if signals:
            report += f"\n**交易信号**: {signals}\n"

        report_path = r.get("report_path", "")
        if report_path:
            rel_path = f"{r['name']}/report.md"
            report += f"\n[查看详细报告 ->]({rel_path})\n"

    report += "\n\n---\n"
    report += f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"

    # 保存报告
    report_path = report_dir / "daily_summary.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    return report_path


def main():
    today = date.today()
    today_str = today.strftime("%Y%m%d")
    today_display = today.strftime("%Y年%m月%d日")

    tasks_dir = Path(__file__).parent
    config_path = tasks_dir / "task_config.json"

    # 读取配置
    print("=" * 60)
    print("每日任务汇总 Runner")
    print("=" * 60)

    try:
        config = load_task_config(config_path)
    except Exception as e:
        print(f"读取配置文件失败: {e}")
        return

    all_tasks = config.get("tasks", [])
    enabled_tasks = [t for t in all_tasks if t.get("enabled", True)]

    if not enabled_tasks:
        print("没有启用的任务")
        return

    print(f"\n共配置 {len(all_tasks)} 个任务，启用 {len(enabled_tasks)} 个")

    # 创建报告目录
    report_dir = project_root / "task_reports" / today_str
    report_dir.mkdir(parents=True, exist_ok=True)

    # 逐一执行任务
    results = []
    for task in enabled_tasks:
        result = run_task(task, tasks_dir)
        results.append(result)

        if result["status"] == "success":
            print(f"  [成功] {result['name']}")
            m = result.get("metrics", {})
            print(f"         收益率: {m.get('return_pct', 0):+.2%}, 夏普: {m.get('sharpe_ratio', 0):.2f}")
        else:
            print(f"  [失败] {result['name']}: {result.get('error', result.get('error_message', ''))}")

    # 生成汇总报告
    print("\n" + "=" * 60)
    print("生成汇总报告...")
    print("=" * 60)

    try:
        summary_path = generate_summary_report(results, report_dir, today_display)
        print(f"\n汇总报告已保存: {summary_path}")
    except Exception as e:
        print(f"生成汇总报告失败: {e}")

    print("\n" + "=" * 60)
    print("全部完成")
    print("=" * 60)


if __name__ == "__main__":
    main()

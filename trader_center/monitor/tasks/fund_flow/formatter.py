"""资金流向任务输出格式化器"""

from typing import Dict, Any

import pandas as pd


def format_fund_flow(value: float) -> str:
    """格式化资金流量显示"""
    if abs(value) >= 1e8:
        return f"{value/1e8:+.2f}亿"
    elif abs(value) >= 1e4:
        return f"{value/1e4:+.2f}万"
    else:
        return f"{value:+.2f}"


def format_market_fund_flow(df: pd.DataFrame) -> str:
    """格式化大盘资金流向输出"""
    if df.empty:
        return "  [!] 该日期暂无数据"

    lines = []
    row = df.iloc[0]
    lines.append(f"\n  [DATA] 主力净流入:     {format_fund_flow(row['main_force_net'])}")
    lines.append(f"     超大单净流入:   {format_fund_flow(row['super_large_net'])}")
    lines.append(f"     大单净流入:     {format_fund_flow(row['large_net'])}")
    lines.append(f"     中单净流入:     {format_fund_flow(row['medium_net'])}")
    lines.append(f"     小单净流入:     {format_fund_flow(row['small_net'])}")

    main_force = row['main_force_net']
    if main_force > 0:
        lines.append(f"\n  [OK] 主力资金净流入，市场情绪偏多")
    else:
        lines.append(f"\n  [WARN]  主力资金净流出，市场情绪偏空")

    return "\n".join(lines)


def format_stock_ranking(df: pd.DataFrame, top_n: int = 10) -> str:
    """格式化个股资金流向排名"""
    if df.empty:
        return "  [!] 该日期暂无数据"

    sorted_df = df.sort_values('fund_flow', ascending=False)

    lines = []
    lines.append(f"\n  {'排名':<4} {'代码':<10} {'名称':<10} {'净流入':>12} {'涨跌幅':>8}")
    lines.append(f"  {'-'*50}")

    for i, (_, row) in enumerate(sorted_df.head(top_n).iterrows(), 1):
        symbol = row['symbol']
        name = row['name'][:8] if row['name'] else '-'
        fund = format_fund_flow(row['fund_flow'])
        change = f"{row['change_pct']:+.2f}%"
        lines.append(f"  {i:<4} {symbol:<10} {name:<10} {fund:>12} {change:>8}")

    return "\n".join(lines)


def format_sector_fund_flow(df: pd.DataFrame, top_n: int = 10, title: str = "板块") -> str:
    """格式化板块资金流向"""
    if df.empty:
        return f"  [WARN]  该日期暂无{title}数据"

    sorted_df = df.sort_values('fund_flow', ascending=False)

    lines = []
    lines.append(f"\n  {'排名':<4} {title:<12} {'净流入':>12} {'涨跌幅':>8} {'领涨股':<10}")
    lines.append(f"  {'-'*55}")

    for i, (_, row) in enumerate(sorted_df.head(top_n).iterrows(), 1):
        sector = row['sector_name'][:10] if row['sector_name'] else '-'
        fund = format_fund_flow(row['fund_flow'])
        change = f"{row['change_pct']:+.2f}%"
        leading = row['leading_stock'][:8] if row['leading_stock'] else '-'
        lines.append(f"  {i:<4} {sector:<12} {fund:>12} {change:>8} {leading:<10}")

    return "\n".join(lines)


def format_header(text: str, width: int = 60) -> str:
    """格式化标题"""
    return f"\n{'='*width}\n {text}\n{'='*width}"


def format_full_report(result: Dict[str, Any], top_n: int = 10) -> str:
    """格式化完整报告"""
    lines = []
    date = result.get('date', 'N/A')

    lines.append(format_header(f"[REPORT] A股资金流向日报 - {date}"))

    # 大盘
    lines.append(format_header("[MARKET] 大盘资金流向"))
    lines.append(format_market_fund_flow(result.get('market', pd.DataFrame())))

    # 个股
    lines.append(format_header(f"[DATA] 个股资金流向 TOP {top_n}"))
    lines.append(format_stock_ranking(result.get('top_stocks', pd.DataFrame()), top_n))

    # 行业
    lines.append(format_header(f"[INDUSTRY] 行业板块资金流向 TOP {top_n}"))
    lines.append(format_sector_fund_flow(result.get('industries', pd.DataFrame()), top_n, "行业"))

    # 概念
    lines.append(format_header(f"[CONCEPT] 概念板块资金流向 TOP {top_n}"))
    lines.append(format_sector_fund_flow(result.get('concepts', pd.DataFrame()), top_n, "概念"))

    lines.append(format_header("[DONE] 执行完成"))

    return "\n".join(lines)


def export_to_file(result: Dict[str, Any], filepath: str) -> None:
    """导出结果到文件"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"A股资金流向报告 - {result.get('date', 'N/A')}\n")
        f.write(f"{'='*60}\n\n")

        # 大盘
        market_df = result.get('market', pd.DataFrame())
        if not market_df.empty:
            f.write("【大盘资金流向】\n")
            row = market_df.iloc[0]
            f.write(f"主力净流入: {format_fund_flow(row['main_force_net'])}\n")
            f.write(f"超大单净流入: {format_fund_flow(row['super_large_net'])}\n")
            f.write(f"大单净流入: {format_fund_flow(row['large_net'])}\n\n")

        # 个股
        top_stocks = result.get('top_stocks', pd.DataFrame())
        if not top_stocks.empty:
            f.write("【个股资金流向 TOP 20】\n")
            sorted_df = top_stocks.sort_values('fund_flow', ascending=False)
            for i, (_, row) in enumerate(sorted_df.head(20).iterrows(), 1):
                f.write(f"{i}. {row['symbol']} {row['name']}: "
                       f"{format_fund_flow(row['fund_flow'])}\n")
            f.write("\n")

        # 行业
        industries = result.get('industries', pd.DataFrame())
        if not industries.empty:
            f.write("【行业板块资金流向 TOP 10】\n")
            sorted_df = industries.sort_values('fund_flow', ascending=False)
            for i, (_, row) in enumerate(sorted_df.head(10).iterrows(), 1):
                f.write(f"{i}. {row['sector_name']}: {format_fund_flow(row['fund_flow'])}\n")
            f.write("\n")

        # 概念
        concepts = result.get('concepts', pd.DataFrame())
        if not concepts.empty:
            f.write("【概念板块资金流向 TOP 10】\n")
            sorted_df = concepts.sort_values('fund_flow', ascending=False)
            for i, (_, row) in enumerate(sorted_df.head(10).iterrows(), 1):
                f.write(f"{i}. {row['sector_name']}: {format_fund_flow(row['fund_flow'])}\n")

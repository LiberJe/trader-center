"""
因子报告生成模块

提供HTML格式的因子分析报告生成功能。
"""

from typing import Optional, Dict, List
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import base64
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


class FactorReport:
    """
    因子分析报告生成器
    
    生成包含因子分析结果的HTML报告。
    
    Example:
        reporter = FactorReport(output_dir='./reports')
        
        # 生成单因子报告
        reporter.generate(
            factor_name='momentum',
            analysis_result=result,
            figures=figures_dict,
        )
        
        # 生成多因子对比报告
        reporter.generate_multi_factor_report(
            analysis_results=results,
            ranking_df=ranking,
        )
    """
    
    def __init__(
        self,
        output_dir: str = './factor_reports',
        template: str = 'default',
    ):
        """
        初始化报告生成器
        
        Args:
            output_dir: 报告输出目录
            template: 报告模板名称
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.template = template
    
    def _figure_to_base64(self, fig) -> str:
        """
        将matplotlib图表转换为base64编码
        
        Args:
            fig: matplotlib Figure对象
        
        Returns:
            base64编码的图片字符串
        """
        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{img_base64}"
    
    def _format_value(self, value, format_str: str = '.4f') -> str:
        """
        格式化数值
        
        Args:
            value: 数值
            format_str: 格式化字符串
        
        Returns:
            格式化后的字符串
        """
        if pd.isna(value):
            return 'N/A'
        if isinstance(value, (int, np.integer)):
            return str(value)
        return f"{value:{format_str}}"
    
    def generate(
        self,
        factor_name: str,
        analysis_result: Dict,
        figures: Dict[str, any] = None,
        score: Dict = None,
        metadata: Dict = None,
        format: str = 'html',
    ) -> str:
        """
        生成因子分析报告
        
        Args:
            factor_name: 因子名称
            analysis_result: 分析结果字典
            figures: 图表字典 {name: Figure}
            score: 评分字典
            metadata: 因子元数据
            format: 输出格式 ('html')
        
        Returns:
            报告文件路径
        
        Example:
            path = reporter.generate(
                factor_name='momentum',
                analysis_result=result,
                figures={'ic': ic_fig, 'layering': layering_fig},
                score={'total_score': 0.75, 'grade': 'B'},
            )
        """
        summary = analysis_result.get('summary', {})
        
        html_content = self._generate_html(
            factor_name=factor_name,
            summary=summary,
            analysis_result=analysis_result,
            figures=figures,
            score=score,
            metadata=metadata,
        )
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{factor_name}_report_{timestamp}.html"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"报告已生成: {filepath}")
        
        return str(filepath)
    
    def _generate_html(
        self,
        factor_name: str,
        summary: Dict,
        analysis_result: Dict,
        figures: Dict,
        score: Dict,
        metadata: Dict,
    ) -> str:
        """
        生成HTML内容
        
        Args:
            factor_name: 因子名称
            summary: 分析摘要
            analysis_result: 完整分析结果
            figures: 图表字典
            score: 评分字典
            metadata: 元数据
        
        Returns:
            HTML字符串
        """
        figures_html = ''
        if figures:
            for name, fig in figures.items():
                img_base64 = self._figure_to_base64(fig)
                figures_html += f'''
                <div class="figure-container">
                    <h3>{name}</h3>
                    <img src="{img_base64}" alt="{name}">
                </div>
                '''
        
        score_html = ''
        if score:
            grade_color = {
                'A': '#28a745',
                'B': '#5cb85c',
                'C': '#ffc107',
                'D': '#fd7e14',
                'F': '#dc3545',
            }.get(score.get('grade', 'F'), '#6c757d')
            
            score_html = f'''
            <div class="score-section">
                <h2>综合评分</h2>
                <div class="score-card">
                    <div class="total-score">
                        <span class="score-value">{score.get('total_score', 0):.2f}</span>
                        <span class="grade" style="background-color: {grade_color}">{score.get('grade', 'F')}</span>
                    </div>
                    <div class="score-details">
                        <div class="score-item">
                            <span>IC有效性</span>
                            <span>{score.get('ic_score', 0):.2f}</span>
                        </div>
                        <div class="score-item">
                            <span>收益贡献</span>
                            <span>{score.get('return_score', 0):.2f}</span>
                        </div>
                        <div class="score-item">
                            <span>稳定性</span>
                            <span>{score.get('stability_score', 0):.2f}</span>
                        </div>
                        <div class="score-item">
                            <span>独立性</span>
                            <span>{score.get('independence_score', 0):.2f}</span>
                        </div>
                    </div>
                </div>
            </div>
            '''
        
        metadata_html = ''
        if metadata:
            metadata_html = '<div class="metadata-section"><h2>因子信息</h2><table class="info-table">'
            for key, value in metadata.items():
                metadata_html += f'<tr><td>{key}</td><td>{value}</td></tr>'
            metadata_html += '</table></div>'
        
        html = f'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>因子分析报告 - {factor_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            margin-bottom: 15px;
            border-left: 4px solid #3498db;
            padding-left: 10px;
        }}
        h3 {{
            color: #555;
            margin: 15px 0 10px 0;
        }}
        .summary-section {{
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .summary-item {{
            background-color: #fff;
            border-radius: 6px;
            padding: 15px;
            text-align: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .summary-item .label {{
            font-size: 14px;
            color: #666;
            margin-bottom: 5px;
        }}
        .summary-item .value {{
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
        }}
        .summary-item .value.positive {{
            color: #27ae60;
        }}
        .summary-item .value.negative {{
            color: #e74c3c;
        }}
        .score-section {{
            margin: 20px 0;
        }}
        .score-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            padding: 25px;
            color: white;
        }}
        .total-score {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 20px;
            margin-bottom: 20px;
        }}
        .score-value {{
            font-size: 48px;
            font-weight: bold;
        }}
        .grade {{
            font-size: 32px;
            font-weight: bold;
            padding: 10px 20px;
            border-radius: 8px;
            color: white;
        }}
        .score-details {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
        }}
        .score-item {{
            background-color: rgba(255,255,255,0.2);
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }}
        .score-item span:first-child {{
            display: block;
            font-size: 14px;
            opacity: 0.9;
        }}
        .score-item span:last-child {{
            font-size: 24px;
            font-weight: bold;
        }}
        .figure-container {{
            margin: 20px 0;
            text-align: center;
        }}
        .figure-container img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #3498db;
            color: white;
        }}
        tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        .info-table td:first-child {{
            font-weight: bold;
            width: 200px;
        }}
        .conclusion {{
            background-color: #e8f4f8;
            border-left: 4px solid #3498db;
            padding: 15px;
            margin: 20px 0;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            text-align: center;
            color: #666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>因子分析报告 - {factor_name}</h1>
        
        {metadata_html}
        
        {score_html}
        
        <div class="summary-section">
            <h2>分析摘要</h2>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="label">IC均值</div>
                    <div class="value {'positive' if summary.get('ic_mean', 0) > 0 else 'negative'}">{self._format_value(summary.get('ic_mean'))}</div>
                </div>
                <div class="summary-item">
                    <div class="label">ICIR</div>
                    <div class="value {'positive' if summary.get('icir', 0) > 0 else 'negative'}">{self._format_value(summary.get('icir'))}</div>
                </div>
                <div class="summary-item">
                    <div class="label">IC>0比例</div>
                    <div class="value">{self._format_value(summary.get('ic_positive_ratio'), '.2%')}</div>
                </div>
                <div class="summary-item">
                    <div class="label">因子收益均值</div>
                    <div class="value {'positive' if summary.get('factor_return_mean', 0) > 0 else 'negative'}">{self._format_value(summary.get('factor_return_mean'))}</div>
                </div>
                <div class="summary-item">
                    <div class="label">因子夏普</div>
                    <div class="value {'positive' if summary.get('factor_sharpe', 0) > 0 else 'negative'}">{self._format_value(summary.get('factor_sharpe'))}</div>
                </div>
                <div class="summary-item">
                    <div class="label">IC偏度</div>
                    <div class="value">{self._format_value(summary.get('ic_skew'))}</div>
                </div>
            </div>
        </div>
        
        <div class="figures-section">
            <h2>分析图表</h2>
            {figures_html}
        </div>
        
        <div class="conclusion">
            <h2>综合评价</h2>
            <p>{self._generate_conclusion(factor_name, summary, score)}</p>
        </div>
        
        <div class="footer">
            <p>报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Trader Center Factor Analysis System</p>
        </div>
    </div>
</body>
</html>
        '''
        
        return html
    
    def _generate_conclusion(
        self,
        factor_name: str,
        summary: Dict,
        score: Dict,
    ) -> str:
        """
        生成综合评价文本
        
        Args:
            factor_name: 因子名称
            summary: 分析摘要
            score: 评分字典
        
        Returns:
            评价文本
        """
        conclusions = []
        
        ic_mean = summary.get('ic_mean', 0)
        icir = summary.get('icir', 0)
        
        if abs(ic_mean) >= 0.05:
            conclusions.append(f"因子 {factor_name} 具有较强的预测能力，IC均值为 {ic_mean:.4f}。")
        elif abs(ic_mean) >= 0.02:
            conclusions.append(f"因子 {factor_name} 具有一定的预测能力，IC均值为 {ic_mean:.4f}。")
        else:
            conclusions.append(f"因子 {factor_name} 的预测能力较弱，IC均值为 {ic_mean:.4f}。")
        
        if abs(icir) >= 1.0:
            conclusions.append(f"因子稳定性优秀，ICIR达到 {icir:.4f}。")
        elif abs(icir) >= 0.5:
            conclusions.append(f"因子稳定性良好，ICIR为 {icir:.4f}。")
        else:
            conclusions.append(f"因子稳定性一般，ICIR为 {icir:.4f}，建议进一步优化。")
        
        if score:
            grade = score.get('grade', 'F')
            total = score.get('total_score', 0)
            conclusions.append(f"综合评分 {total:.2f}，评级 {grade}。")
            
            if grade in ['A', 'B']:
                conclusions.append("该因子具有较好的投资价值，建议纳入因子库。")
            elif grade == 'C':
                conclusions.append("该因子表现中等，可考虑与其他因子组合使用。")
            else:
                conclusions.append("该因子表现不佳，建议进一步研究或放弃。")
        
        return ' '.join(conclusions)
    
    def generate_multi_factor_report(
        self,
        analysis_results: Dict[str, Dict],
        ranking_df: pd.DataFrame,
        figures: Dict[str, any] = None,
        format: str = 'html',
    ) -> str:
        """
        生成多因子对比报告
        
        Args:
            analysis_results: 分析结果字典
            ranking_df: 排名DataFrame
            figures: 图表字典
            format: 输出格式
        
        Returns:
            报告文件路径
        """
        html_content = self._generate_multi_factor_html(
            analysis_results=analysis_results,
            ranking_df=ranking_df,
            figures=figures,
        )
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"multi_factor_report_{timestamp}.html"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"多因子报告已生成: {filepath}")
        
        return str(filepath)
    
    def _generate_multi_factor_html(
        self,
        analysis_results: Dict[str, Dict],
        ranking_df: pd.DataFrame,
        figures: Dict,
    ) -> str:
        """
        生成多因子对比HTML
        """
        figures_html = ''
        if figures:
            for name, fig in figures.items():
                img_base64 = self._figure_to_base64(fig)
                figures_html += f'''
                <div class="figure-container">
                    <h3>{name}</h3>
                    <img src="{img_base64}" alt="{name}">
                </div>
                '''
        
        ranking_table = ranking_df.to_html(classes='ranking-table', float_format='%.4f')
        
        html = f'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>多因子对比报告</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-left: 4px solid #3498db;
            padding-left: 10px;
        }}
        .ranking-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        .ranking-table th {{
            background-color: #3498db;
            color: white;
            padding: 12px;
            text-align: left;
        }}
        .ranking-table td {{
            border: 1px solid #ddd;
            padding: 10px;
        }}
        .ranking-table tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        .figure-container {{
            margin: 20px 0;
            text-align: center;
        }}
        .figure-container img {{
            max-width: 100%;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            text-align: center;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>多因子对比报告</h1>
        
        <h2>因子排名</h2>
        {ranking_table}
        
        <h2>对比图表</h2>
        {figures_html}
        
        <div class="footer">
            <p>报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Trader Center Factor Analysis System</p>
        </div>
    </div>
</body>
</html>
        '''
        
        return html

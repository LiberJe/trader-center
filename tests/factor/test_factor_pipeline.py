"""
因子流水线模块测试
"""

import pytest
import pandas as pd
import numpy as np


def create_test_data(n_dates: int = 100, n_assets: int = 20):
    """创建测试数据"""
    dates = pd.date_range('2023-01-01', periods=n_dates, freq='B')
    assets = [f'Asset_{i:02d}' for i in range(n_assets)]
    
    price_data = pd.DataFrame(
        np.random.randn(n_dates, n_assets).cumsum(axis=0) + 100,
        index=dates,
        columns=assets
    )
    
    factor_data = price_data.pct_change(20)
    
    return price_data, factor_data


class TestScoring:
    """测试因子评分模块"""
    
    def test_factor_scorer_init(self):
        """测试评分器初始化"""
        from trader_center.factor.mining.scoring import FactorScorer
        
        scorer = FactorScorer()
        assert scorer.ic_threshold == 0.02
        assert scorer.icir_threshold == 0.5
        
        scorer2 = FactorScorer(ic_threshold=0.03, icir_threshold=0.6)
        assert scorer2.ic_threshold == 0.03
        assert scorer2.icir_threshold == 0.6
    
    def test_factor_scorer_score(self):
        """测试评分计算"""
        from trader_center.factor.mining.scoring import FactorScorer
        
        scorer = FactorScorer()
        
        result = {
            'summary': {
                'ic_mean': 0.05,
                'icir': 0.8,
                'factor_return_mean': 0.02,
                'factor_sharpe': 1.5,
                'ic_positive_ratio': 0.6,
            }
        }
        
        score = scorer.score(result)
        
        assert 'total_score' in score
        assert 'grade' in score
        assert score['grade'] in ['A', 'B', 'C', 'D', 'F']
    
    def test_rank_factors(self):
        """测试因子排名"""
        from trader_center.factor.mining.scoring import FactorScorer
        
        scorer = FactorScorer()
        
        results = {
            'factor1': {
                'summary': {
                    'ic_mean': 0.05,
                    'icir': 0.8,
                    'factor_return_mean': 0.02,
                    'factor_sharpe': 1.5,
                    'ic_positive_ratio': 0.6,
                }
            },
            'factor2': {
                'summary': {
                    'ic_mean': 0.02,
                    'icir': 0.3,
                    'factor_return_mean': 0.01,
                    'factor_sharpe': 0.5,
                    'ic_positive_ratio': 0.55,
                }
            },
        }
        
        ranking = scorer.rank_factors(results)
        
        assert len(ranking) == 2
        assert ranking.iloc[0]['total_score'] >= ranking.iloc[1]['total_score']


class TestVisualization:
    """测试可视化模块"""
    
    def test_visualizer_init(self):
        """测试可视化器初始化"""
        from trader_center.factor.mining.visualization import FactorVisualizer
        
        viz = FactorVisualizer()
        assert viz.figsize_scale == 1.0
        
        viz2 = FactorVisualizer(figsize_scale=1.5)
        assert viz2.figsize_scale == 1.5
    
    def test_plot_factor_distribution(self):
        """测试因子分布图"""
        from trader_center.factor.mining.visualization import FactorVisualizer
        import matplotlib.pyplot as plt
        
        viz = FactorVisualizer()
        
        data = pd.Series(np.random.randn(1000))
        
        fig = viz.plot_factor_distribution(data, show_stats=True)
        
        assert fig is not None
        
        plt.close(fig)


class TestPipeline:
    """测试流水线模块"""
    
    def test_pipeline_init(self):
        """测试流水线初始化"""
        from trader_center.factor.mining.pipeline import FactorAnalysisPipeline
        
        pipeline = FactorAnalysisPipeline()
        
        assert pipeline.preprocessing_config is not None
        assert pipeline.analysis_config is not None
    
    def test_pipeline_preprocessing(self):
        """测试预处理"""
        from trader_center.factor.mining.pipeline import FactorAnalysisPipeline
        
        pipeline = FactorAnalysisPipeline()
        
        _, factor_data = create_test_data()
        
        processed = pipeline._preprocess(factor_data)
        
        assert processed.shape == factor_data.shape
    
    def test_pipeline_run(self):
        """测试流水线运行"""
        from trader_center.factor.mining.pipeline import FactorAnalysisPipeline
        
        pipeline = FactorAnalysisPipeline(use_alphalens=False)
        
        price_data, factor_data = create_test_data()
        
        result = pipeline.run(
            factor_name='test_factor',
            factor_df=factor_data,
            price_df=price_data,
            preprocessing=True,
            scoring=True,
            visualize=False,
        )
        
        assert 'summary' in result
        assert 'score' in result


class TestReport:
    """测试报告模块"""
    
    def test_report_init(self):
        """测试报告初始化"""
        from trader_center.factor.mining.report import FactorReport
        import tempfile
        import shutil
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            reporter = FactorReport(output_dir=temp_dir)
            
            assert reporter.output_dir.exists()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestMonotonicity:
    """测试单调性计算"""
    
    def test_compute_monotonicity(self):
        """测试单调性计算"""
        from trader_center.factor.mining.scoring import compute_monotonicity
        
        returns = pd.DataFrame({
            'Q1': [0.01, 0.02, 0.015],
            'Q2': [0.02, 0.03, 0.025],
            'Q3': [0.03, 0.04, 0.035],
            'Q4': [0.04, 0.05, 0.045],
            'Q5': [0.05, 0.06, 0.055],
        })
        
        monotonicity = compute_monotonicity(returns)
        
        assert monotonicity > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

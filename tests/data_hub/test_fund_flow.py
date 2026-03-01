"""资金流向数据测试"""
import pytest
from datetime import date

from trader_center.data_hub.models import (
    MarketFundFlow,
    StockFundFlow,
    SectorFundFlow,
)


class TestMarketFundFlow:
    """大盘资金流向模型测试"""

    def test_create_market_fund_flow(self):
        """测试创建大盘资金流向数据"""
        mf = MarketFundFlow(
            date=date(2024, 1, 15),
            market="all",
            main_force_net=100.5,
            super_large_net=50.2,
            large_net=30.1,
            medium_net=10.0,
            small_net=-20.3,
            total_amount=5000.0,
        )
        assert mf.date == date(2024, 1, 15)
        assert mf.market == "all"
        assert mf.main_force_net == 100.5
        assert mf.total_amount == 5000.0

    def test_market_fund_flow_is_frozen(self):
        """测试数据不可变"""
        mf = MarketFundFlow(
            date=date(2024, 1, 15),
            market="all",
            main_force_net=100.5,
            super_large_net=50.2,
            large_net=30.1,
            medium_net=10.0,
            small_net=-20.3,
            total_amount=5000.0,
        )
        with pytest.raises(Exception):
            mf.main_force_net = 200.0


class TestStockFundFlow:
    """个股资金流向模型测试"""

    def test_create_stock_fund_flow(self):
        """测试创建个股资金流向数据"""
        sf = StockFundFlow(
            date=date(2024, 1, 15),
            symbol="000001.SZ",
            name="平安银行",
            close_price=10.5,
            change_pct=2.5,
            fund_flow=1000.0,
            flow_ratio=0.5,
            main_force_net=800.0,
        )
        assert sf.symbol == "000001.SZ"
        assert sf.name == "平安银行"
        assert sf.fund_flow == 1000.0


class TestSectorFundFlow:
    """板块资金流向模型测试"""

    def test_create_sector_fund_flow(self):
        """测试创建板块资金流向数据"""
        sef = SectorFundFlow(
            date=date(2024, 1, 15),
            sector_type="industry",
            sector_name="银行",
            fund_flow=5000.0,
            change_pct=1.2,
            leading_stock="平安银行",
            leading_stock_change=2.5,
        )
        assert sef.sector_type == "industry"
        assert sef.sector_name == "银行"
        assert sef.fund_flow == 5000.0


class TestFundFlowStorage:
    """资金流向存储测试"""

    @pytest.fixture
    def config(self, tmp_path):
        from trader_center.data_hub.config import DataHubConfig
        return DataHubConfig(data_dir=tmp_path)

    @pytest.fixture
    def storage(self, config):
        from trader_center.data_hub.storage.sqlite_store import SQLiteStorage
        return SQLiteStorage(config)

    def test_save_and_get_market_fund_flow(self, storage):
        """测试保存和读取大盘资金流向"""
        mf = MarketFundFlow(
            date=date(2024, 1, 15),
            market="all",
            main_force_net=100.5,
            super_large_net=50.2,
            large_net=30.1,
            medium_net=10.0,
            small_net=-20.3,
            total_amount=5000.0,
        )
        storage.save_market_fund_flow(mf)

        retrieved = storage.get_market_fund_flow(date(2024, 1, 15))
        assert retrieved is not None
        assert retrieved.main_force_net == 100.5
        assert retrieved.market == "all"

    def test_get_nonexistent_market_fund_flow(self, storage):
        """测试读取不存在的数据"""
        result = storage.get_market_fund_flow(date(2020, 1, 1))
        assert result is None

    def test_save_and_get_stock_fund_flow(self, storage):
        """测试保存和读取个股资金流向"""
        stocks = [
            StockFundFlow(
                date=date(2024, 1, 15),
                symbol="000001.SZ",
                name="平安银行",
                close_price=10.5,
                change_pct=2.5,
                fund_flow=1000.0,
                flow_ratio=0.5,
                main_force_net=800.0,
            ),
            StockFundFlow(
                date=date(2024, 1, 15),
                symbol="000002.SZ",
                name="万科A",
                close_price=15.0,
                change_pct=-1.5,
                fund_flow=-500.0,
                flow_ratio=-0.3,
                main_force_net=-400.0,
            ),
        ]
        storage.save_stock_fund_flow(stocks)

        retrieved = storage.get_stock_fund_flow(date(2024, 1, 15), limit=10)
        assert len(retrieved) == 2
        assert retrieved[0].symbol == "000001.SZ"

    def test_save_and_get_sector_fund_flow(self, storage):
        """测试保存和读取板块资金流向"""
        sectors = [
            SectorFundFlow(
                date=date(2024, 1, 15),
                sector_type="industry",
                sector_name="银行",
                fund_flow=5000.0,
                change_pct=1.2,
                leading_stock="平安银行",
                leading_stock_change=2.5,
            ),
            SectorFundFlow(
                date=date(2024, 1, 15),
                sector_type="industry",
                sector_name="地产",
                fund_flow=-3000.0,
                change_pct=-0.8,
                leading_stock="万科A",
                leading_stock_change=-1.5,
            ),
        ]
        storage.save_sector_fund_flow(sectors)

        retrieved = storage.get_sector_fund_flow(
            date(2024, 1, 15), sector_type="industry"
        )
        assert len(retrieved) == 2

    def test_get_sector_fund_flow_all_types(self, storage):
        """测试读取所有类型的板块资金流向"""
        sectors = [
            SectorFundFlow(
                date=date(2024, 1, 15),
                sector_type="industry",
                sector_name="银行",
                fund_flow=5000.0,
                change_pct=1.2,
                leading_stock="平安银行",
                leading_stock_change=2.5,
            ),
            SectorFundFlow(
                date=date(2024, 1, 15),
                sector_type="concept",
                sector_name="人工智能",
                fund_flow=8000.0,
                change_pct=3.0,
                leading_stock="科大讯飞",
                leading_stock_change=5.0,
            ),
        ]
        storage.save_sector_fund_flow(sectors)

        # 获取所有类型
        all_sectors = storage.get_sector_fund_flow(date(2024, 1, 15))
        assert len(all_sectors) == 2

        # 只获取 industry
        industries = storage.get_sector_fund_flow(
            date(2024, 1, 15), sector_type="industry"
        )
        assert len(industries) == 1
        assert industries[0].sector_name == "银行"

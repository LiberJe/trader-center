"""
python -m trader_center.backtest
"""

from .cli import main

if __name__ == '__main__':
    import sys
    sys.exit(main())

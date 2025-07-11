from .market_api import MarketAPI
from .trading_api import TradingAPI
from config import get_api_credentials

class APIClient:
    def __init__(self):
        api_key, api_secret = get_api_credentials()
        self.market_api = MarketAPI(api_key, api_secret)
        self.trading_api = TradingAPI(api_key, api_secret)

    def get_market_api(self) -> MarketAPI:
        return self.market_api

    def get_trading_api(self) -> TradingAPI:
        return self.trading_api
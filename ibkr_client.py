import pandas as pd
from ib_insync import IB, util, Contract, MarketOrder

class IbkrClient:
    def __init__(self, config_path="config.yaml"):
        import yaml
        cfg = yaml.safe_load(open(config_path))
        self.host = cfg['IBKR']['host']
        self.port = cfg['IBKR']['port']
        self.clientId = cfg['IBKR']['clientId']
        self.account = cfg['IBKR']['account']
        self.ib = IB()
        self.ib.connect(self.host, self.port, self.clientId)
    
    def get_ohlc(self, symbol, timeframe, count=100):
        # Adapter selon le type de contrat (Forex, CFD, etc.)
        contract = Contract()
        contract.symbol = symbol
        contract.secType = 'CASH'
        contract.exchange = 'IDEALPRO'
        contract.currency = symbol[-3:]
        bars = self.ib.reqHistoricalData(
            contract,
            endDateTime='',
            durationStr=f'{count} D',
            barSizeSetting=timeframe,
            whatToShow='MIDPOINT',
            useRTH=False,
            formatDate=1
        )
        df = util.df(bars)
        return df
    
    def place_order(self, symbol, action, quantity):
        contract = Contract()
        contract.symbol = symbol
        contract.secType = 'CASH'
        contract.exchange = 'IDEALPRO'
        contract.currency = symbol[-3:]
        order = MarketOrder(action, quantity)
        trade = self.ib.placeOrder(contract, order)
        return trade
    
    def get_account_summary(self):
        acc = self.ib.accountSummary()
        return acc

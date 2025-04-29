import pandas as pd

class Backtester:
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
    
    def backtest(self, data, signals):
        """
        Executa o backtest baseado nos sinais gerados
        """
        portfolio = pd.DataFrame(index=signals.index)
        portfolio['price'] = signals['price']
        portfolio['signal'] = signals['signal']
        
        # Posições (1 = comprado, -1 = vendido, 0 = neutro)
        portfolio['position'] = portfolio['signal'].diff()
        
        # Capital inicial
        portfolio['capital'] = self.initial_capital
        
        # Calcula retornos diários
        portfolio['daily_return'] = portfolio['price'].pct_change()
        
        # Retornos da estratégia
        portfolio['strategy_return'] = portfolio['position'].shift(1) * portfolio['daily_return']
        
        # Retorno acumulado
        portfolio['cumulative_return'] = (1 + portfolio['strategy_return']).cumprod()
        
        return portfolio

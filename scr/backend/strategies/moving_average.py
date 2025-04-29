import pandas as pd

class MovingAverageStrategy:
    def __init__(self, short_window=50, long_window=200):
        self.short_window = short_window
        self.long_window = long_window
    
    def generate_signals(self, data):
        """
        Gera sinais de compra/venda baseados em crossover de médias móveis
        """
        signals = pd.DataFrame(index=data.index)
        signals['price'] = data['close']
        signals['short_ma'] = data['close'].rolling(self.short_window).mean()
        signals['long_ma'] = data['close'].rolling(self.long_window).mean()
        
        # Sinal de compra (1) quando a média curta cruza a longa para cima
        signals['signal'] = 0
        signals.loc[signals['short_ma'] > signals['long_ma'], 'signal'] = 1
        
        # Sinal de venda (-1) quando a média curta cruza a longa para baixo
        signals.loc[signals['short_ma'] < signals['long_ma'], 'signal'] = -1
        
        return signals

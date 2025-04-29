# /src/backend/data_handlers/binance_data.py
from binance.client import Client
import pandas as pd
import os
import time
from datetime import datetime

class BinanceDataHandler:
    def __init__(self):
        # Configurações (substitua pelas suas chaves)
        self.API_KEY = 'KJvozVQCG99RMGODQalszOjw9SXpaQOlOXjV0igqutcea7M2bK7sQc7lvLLlonM4'
        self.API_SECRET = 'FL2IfSSEHVepMWINfEzQ9vFcHNTVn7yHvsD29GMpz5A0E5nqM4LY3WXeTPnYoyCN'
        self.client = Client(self.API_KEY, self.API_SECRET)
        
        # Configurações de diretório
        self.BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.DATA_DIR = os.path.join(self.BASE_DIR, 'data', 'binance')
        os.makedirs(self.DATA_DIR, exist_ok=True)

    def fetch_klines(self, symbol, interval, start_date, end_date=None):
        """Baixa dados históricos da Binance"""
        print(f"Baixando {symbol} {interval} desde {start_date}...")
        try:
            klines = self.client.get_historical_klines(
                symbol=symbol,
                interval=interval,
                start_str=start_date,
                end_str=end_date
            )
            
            cols = [
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ]
            df = pd.DataFrame(klines, columns=cols)
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            numeric_cols = ['open', 'high', 'low', 'close', 'volume', 
                          'quote_volume', 'trades', 'taker_buy_base', 'taker_buy_quote']
            df[numeric_cols] = df[numeric_cols].astype(float)
            
            return df
        
        except Exception as e:
            print(f"Erro ao baixar {symbol} {interval}: {str(e)}")
            return None

    def save_to_csv(self, df, symbol, interval):
        """Salva os dados em CSV"""
        if df is not None and not df.empty:
            filename = f"{symbol}_{interval}.csv".replace("/", "-")
            filepath = os.path.join(self.DATA_DIR, filename)
            df.to_csv(filepath, index=False)
            print(f"Dados salvos em: {filepath}")
            return filepath
        return None

    def load_from_csv(self, symbol, interval):
        """Carrega dados salvos de um CSV"""
        filename = f"{symbol}_{interval}.csv".replace("/", "-")
        filepath = os.path.join(self.DATA_DIR, filename)
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        return None

    def preprocess_data(self, df):
        """Pré-processamento dos dados"""
        if df is None or df.empty:
            return None
            
        cols_to_keep = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        df = df[cols_to_keep].copy()
        df.set_index('timestamp', inplace=True)
        df['returns'] = df['close'].pct_change()
        df.dropna(inplace=True)
        return df

    def download_all_intervals(self, symbol='BTCUSDT', intervals=None, start_date="1 Jan 2017"):
        """Baixa múltiplos intervalos de tempo"""
        if intervals is None:
            intervals = [
                Client.KLINE_INTERVAL_1MINUTE,
                Client.KLINE_INTERVAL_5MINUTE,
                Client.KLINE_INTERVAL_15MINUTE,
                Client.KLINE_INTERVAL_1HOUR,
                Client.KLINE_INTERVAL_4HOUR,
                Client.KLINE_INTERVAL_1DAY
            ]
        
        print(f"Iniciando download de dados para {symbol}...")
        for interval in intervals:
            df = self.fetch_klines(symbol, interval, start_date)
            self.save_to_csv(df, symbol, interval)
            time.sleep(1)  # Evitar rate limit

# Exemplo de uso integrado com backtesting
if __name__ == "__main__":
    # 1. Baixar dados
    data_handler = BinanceDataHandler()
    data_handler.download_all_intervals()
    
    # 2. Carregar e pré-processar dados
    df = data_handler.load_from_csv('BTCUSDT', '1d')
    processed_data = data_handler.preprocess_data(df)
    
    if processed_data is not None:
        print("\nDados carregados com sucesso! Exemplo:")
        print(processed_data.head())
        
        # 3. Exemplo de integração com estratégia (simplificado)
        print("\nExemplo de backtesting:")
        from strategies.moving_average import MovingAverageStrategy
        
        strategy = MovingAverageStrategy(short_window=10, long_window=30)
        signals = strategy.generate_signals(processed_data)
        
        print("\nSinais gerados:")
        print(signals.tail())
    else:
        print("Erro ao carregar dados para backtesting")

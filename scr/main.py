# /src/main.py
import sys
import os
from datetime import datetime

# Adiciona o diretório backend ao PATH para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.data_handlers.binance_data import BinanceDataHandler
from backend.strategies.moving_average import MovingAverageStrategy

def main():
    print("=== Sistema de Backtesting ===")
    
    # 1. Configuração
    symbol = "BTCUSDT"
    interval = "1d"  # Teste com daily primeiro para ser rápido
    start_date = "1 Jan 2020"
    
    # 2. Baixar/Recarregar dados
    data_handler = BinanceDataHandler()
    
    print("\n[1/4] Carregando dados...")
    df = data_handler.load_from_csv(symbol, interval)
    
    if df is None:
        print(f"Dados não encontrados. Baixando novos dados desde {start_date}...")
        data_handler.download_all_intervals(symbol=symbol, intervals=[interval], start_date=start_date)
        df = data_handler.load_from_csv(symbol, interval)
    
    # 3. Pré-processamento
    print("\n[2/4] Pré-processando dados...")
    processed_data = data_handler.preprocess_data(df)
    print(processed_data.tail(3))
    
    # 4. Estratégia
    print("\n[3/4] Gerando sinais...")
    strategy = MovingAverageStrategy(short_window=10, long_window=30)
    signals = strategy.generate_signals(processed_data)
    print(signals.tail(3))
    
    # 5. Backtest (simplificado)
    print("\n[4/4] Simulando resultados...")
    initial_balance = 10000
    balance = initial_balance
    position = 0
    
    for i, row in signals.iterrows():
        if row['signal'] == 1 and position <= 0:  # Compra
            position = balance / row['price']
            balance = 0
            print(f"{i.date()} - COMPRA a ${row['price']:.2f}")
        elif row['signal'] == -1 and position > 0:  # Venda
            balance = position * row['price']
            position = 0
            print(f"{i.date()} - VENDA a ${row['price']:.2f}")
    
    # Resultado final
    final_balance = balance if balance > 0 else position * signals.iloc[-1]['price']
    print(f"\nResultado: ${initial_balance:.2f} -> ${final_balance:.2f}")
    print(f"Retorno: {(final_balance/initial_balance-1)*100:.2f}%")

if __name__ == "__main__":
    main()

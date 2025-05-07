
# /src/main.py
import sys
import os

# Adiciona o diretório backend ao PATH para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.backtest_service import (
    run_backtest,
    get_available_strategies,
    get_available_intervals,
)

def main():
    print("=== Sistema de Backtesting FLEXÍVEL ===\n")

    # 1. Exibe listas disponíveis para escolha manual
    strategies = get_available_strategies()
    intervals = get_available_intervals()

    print("Estratégias disponíveis:")
    for idx, s in enumerate(strategies, 1):
        print(f"{idx} - {s}")
    print("\nIntervalos disponíveis:")
    for idx, i in enumerate(intervals, 1):
        print(f"{idx} - {i}")

    # 2. Parâmetros de seleção
    try:
        strategy_idx = int(input("\nEscolha o número da estratégia: ")) - 1
        interval_idx = int(input("Escolha o número do intervalo: ")) - 1
        chosen_strategy = strategies[strategy_idx]
        chosen_interval = intervals[interval_idx]
    except (ValueError, IndexError):
        print("Seleção inválida. Usando valores padrão.")
        chosen_strategy = strategies[0]
        chosen_interval = intervals[-1]

    symbol = "BTCUSDT"
    start_date = "1 Jan 2020"
    initial_balance = 10000

    print(f"\nRodando com estratégia: {chosen_strategy}, intervalo: {chosen_interval}")

    # 3. Parâmetros específicos da estratégia
    strategy_params = {}
    if "MovingAverage" in chosen_strategy:
        try:
            short_window = int(input("Janela curta (padrão 10): ") or "10")
            long_window = int(input("Janela longa (padrão 30): ") or "30")
            strategy_params = {"short_window": short_window, "long_window": long_window}
        except ValueError:
            print("Valores inválidos. Usando padrões.")
            strategy_params = {"short_window": 10, "long_window": 30}

    try:
        fee_pct = float(input("Taxa de trading (em %, padrão 0.1): ").replace(",", ".") or "0.1")
    except ValueError:
        fee_pct = 0.1
    fee_pct = fee_pct / 100

    # 4. Executa o backtest
    result = run_backtest(
        strategy_name=chosen_strategy,
        interval=chosen_interval,
        symbol=symbol,
        start_date=start_date,
        initial_balance=initial_balance,
        strategy_params=strategy_params,
        fee_pct=fee_pct
    )

    # 5. Exibe só as métricas quantitativas
    if "error" in result:
        print(f"Erro ao rodar backtest: {result['error']}")
        return

    print("\n====📊 Resultados do Backtest ====")
    print(f"Ativo: {result['symbol']}")
    print(f"Estratégia: {result['strategy']}")
    print(f"Intervalo: {result['interval']}")
    print(f"Taxa trading considerada: {result.get('trade_fee_pct', 0)*100:.3f}%")

    print(f"\n💰 Lucro Total: {result['total_return']:.2f}  ({result['total_return_pct']:.2f}%)")
    print(f"🏅 Retorno médio por trade: {result['avg_return_per_trade']:.2f}%")
    print(f"📅 Retorno médio diário: {result['avg_daily_return']:.2f}%")
    print(f"📉 Máximo Drawdown: {result['max_drawdown_value']:.2f} ({result['max_drawdown_pct']:.2f}%)")
    print(f"⏳ Tempo de recuperação (períodos): {result['recovery_time_periods'] if result['recovery_time_periods'] is not None else 'N/A'}")
    print(f"🔁 Taxa de acerto: {result['win_rate_pct']:.2f}%")
    print(f"💸 Profit Factor: {result['profit_factor']}")
    print(f"📦 Número de operações: {result['n_trades']}")
    print(f"⚖️ Sharpe Ratio: {result['sharpe_ratio']}")
    print(f"🪙 Volatilidade anualizada: {result['volatility_pct']}%")
    print("==================================\n")

if __name__ == "__main__":
    main()

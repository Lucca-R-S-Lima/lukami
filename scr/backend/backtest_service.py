
import os
import importlib
import numpy as np
import pandas as pd
from backend.data_handlers.binance_data import BinanceDataHandler

STRATEGY_DIR = os.path.join(os.path.dirname(__file__), "strategies")

def get_available_strategies():
    strategies = []
    for fname in os.listdir(STRATEGY_DIR):
        if fname.endswith(".py") and not fname.startswith("_"):
            module_name = fname[:-3]
            module = importlib.import_module(f"backend.strategies.{module_name}")
            for attr in dir(module):
                if attr.endswith("Strategy"):
                    strategies.append(attr)
    return strategies

def get_available_intervals():
    return ["1m", "5m", "15m", "1h", "4h", "1d"]

def _compute_max_drawdown(equity_curve):
    """Retorna drawdown máximo e onde ocorreu."""
    roll_max = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve - roll_max) / roll_max
    max_dd = drawdown.min()
    end = np.argmin(drawdown)
    start = np.argmax(equity_curve[:end+1])
    return max_dd, start, end

def _compute_recovery_time(equity_curve, start, end):
    """Calcula número de períodos para voltar ao topo após maior drawdown."""
    if end == len(equity_curve) - 1:
        return None  # Nunca recuperou
    peak_value = equity_curve[start]
    for i in range(end, len(equity_curve)):
        if equity_curve[i] >= peak_value:
            return i - end
    return None  # Nunca recuperou

def run_backtest(
    strategy_name, 
    interval, 
    symbol="BTCUSDT", 
    start_date="1 Jan 2020", 
    initial_balance=10000, 
    strategy_params=None, 
    fee_pct=0.001
):
    """
    Executa o backtest para a estratégia e intervalo selecionados.
    Retorna um dicionário só com estatísticas quantitativas relevantes.
    """
    # 1. Carregar dados
    data_handler = BinanceDataHandler()
    df = data_handler.load_from_csv(symbol, interval)
    if df is None:
        data_handler.download_all_intervals(symbol=symbol, intervals=[interval], start_date=start_date)
        df = data_handler.load_from_csv(symbol, interval)
    processed_data = data_handler.preprocess_data(df)
    if processed_data is None or processed_data.empty:
        return {"error": "Dados insuficientes para backtest."}

    # 2. Carregar estratégia de forma dinâmica
    found = False
    for fname in os.listdir(STRATEGY_DIR):
        if fname.endswith(".py") and not fname.startswith("_"):
            module_name = fname[:-3]
            module = importlib.import_module(f"backend.strategies.{module_name}")
            if hasattr(module, strategy_name):
                StrategyClass = getattr(module, strategy_name)
                found = True
                break
    if not found:
        return {"error": f"Estratégia '{strategy_name}' não encontrada."}

    # 3. Gerar sinais
    params = strategy_params or {}
    strategy = StrategyClass(**params)
    signals = strategy.generate_signals(processed_data)
    if signals.empty:
        return {"error": "Nenhum sinal gerado."}
    signals = signals.copy().dropna(subset=['signal'])
    signals['shifted_signal'] = signals['signal'].shift(1)
    joined = signals.join(processed_data[['open']], how='inner')
    joined = joined.iloc[1:]

    # Para computar equity: Executa trade na próxima barra, só alterna entre posição e caixa
    balance = initial_balance
    position = 0
    equity_curve = [balance]
    trade_returns = []
    trade_outcomes = []
    trades = []
    last_trade_day = None

    for i, row in joined.iterrows():
        sig = row['shifted_signal']
        open_price = row['open']
        if sig == 1 and position <= 0:
            fee = balance * fee_pct
            balance_after_fee = balance - fee
            position = balance_after_fee / open_price
            trades.append({'dt': i, 'type': 'BUY', 'price': open_price, 'fee': fee, 'balance': balance, 'position': position})
            balance = 0
            last_trade_day = i
        elif sig == -1 and position > 0:
            gross = position * open_price
            fee = gross * fee_pct
            proceeds = gross - fee
            trade_returns.append((proceeds - (trades[-1]['balance'] if trades else initial_balance))/ (trades[-1]['balance'] if trades else initial_balance))
            trade_outcomes.append(proceeds > (trades[-1]['balance'] if trades else initial_balance))
            balance = proceeds
            trades.append({'dt': i, 'type': 'SELL', 'price': open_price, 'fee': fee, 'balance': balance, 'position': 0})
            position = 0
            last_trade_day = i
        # equity curve após cada candle
        cur_equity = balance + position * open_price
        equity_curve.append(cur_equity)
    
    # Se posição aberta ao final, liquida
    if position > 0:
        gross = position * joined.iloc[-1]['open']
        fee = gross * fee_pct
        final_balance = gross - fee
    else:
        final_balance = balance
    equity_curve = np.array(equity_curve)
    returns = pd.Series(np.diff(equity_curve) / equity_curve[:-1])

    total_return = final_balance - initial_balance
    total_return_pct = (final_balance / initial_balance - 1) * 100

    # Métricas avançadas
    avg_ret_per_trade = np.mean(trade_returns) if trade_returns else 0
    avg_daily_ret = returns.mean() if not returns.empty else 0
    max_dd, peak_idx, dd_idx = _compute_max_drawdown(equity_curve)
    max_dd_pct = abs(max_dd) * 100
    recov_time = _compute_recovery_time(equity_curve, peak_idx, dd_idx)
    win_rate = (np.sum(trade_outcomes) / len(trade_outcomes)) * 100 if trade_outcomes else 0
    gross_profit = np.sum([r for r in trade_returns if r > 0]) * initial_balance
    gross_loss = -np.sum([r for r in trade_returns if r < 0]) * initial_balance
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else np.inf
    n_trades = len(trade_returns)
    rf = 0
    excess_ret = returns - rf
    sharpe = (excess_ret.mean() / (excess_ret.std() + 1e-9)) * np.sqrt(252) if not returns.empty else np.nan
    volatility = returns.std() * np.sqrt(252) if not returns.empty else np.nan

    return {
        "symbol": symbol,
        "interval": interval,
        "strategy": strategy_name,
        "initial_balance": round(initial_balance, 2),
        "final_balance": round(final_balance, 2),
        "total_return": round(total_return, 2),
        "total_return_pct": round(total_return_pct, 2),
        "avg_return_per_trade": round(avg_ret_per_trade * 100, 2),
        "avg_daily_return": round(avg_daily_ret * 100, 2),
        "max_drawdown_pct": round(max_dd_pct, 2),
        "max_drawdown_value": round(abs(max_dd)*initial_balance, 2),
        "recovery_time_periods": recov_time,
        "win_rate_pct": round(win_rate, 2),
        "profit_factor": round(profit_factor, 2) if np.isfinite(profit_factor) else "N/D",
        "n_trades": n_trades,
        "sharpe_ratio": round(sharpe, 2) if not np.isnan(sharpe) else "N/D",
        "volatility_pct": round(volatility * 100, 2) if not np.isnan(volatility) else "N/D",
        "trade_fee_pct": fee_pct,
    }

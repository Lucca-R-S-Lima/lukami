
import os
import importlib
import numpy as np
import pandas as pd
from backend.data_handlers.binance_data import BinanceDataHandler
from backend.trade_audit import audit_trades

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
    return max_dd, start, end, drawdown

def _compute_recovery_time(equity_curve, start, end):
    """Calcula número de períodos para voltar ao topo após maior drawdown."""
    if end == len(equity_curve) - 1:
        return None  # Nunca recuperou
    peak_value = equity_curve[start]
    for i in range(end, len(equity_curve)):
        if equity_curve[i] >= peak_value:
            return i - end
    return None  # Nunca recuperou

def _compute_cagr(initial_balance, final_balance, n_days):
    """Taxa de crescimento anual composta (CAGR)"""
    if n_days == 0: return 0
    years = n_days / 365
    if years <= 0 or initial_balance <= 0:
        return 0
    cagr = (final_balance / initial_balance) ** (1/years) - 1
    return cagr * 100  # percent

def _get_benchmark_hold_returns(processed_data, initial_balance):
    """Simula buy & hold: compra tudo na primeira barra, vende tudo na última."""
    open0 = processed_data["open"].iloc[0]
    openN = processed_data["open"].iloc[-1]
    shares = initial_balance / open0
    final_balance = shares * openN
    total_return = final_balance - initial_balance
    pct_return = (final_balance / initial_balance - 1) * 100
    equity_curve = processed_data["open"] * shares
    return {
        "final_balance": final_balance,
        "total_return": total_return,
        "total_return_pct": pct_return,
        "equity_curve": list(equity_curve)
    }

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
    Retorna um dicionário só com estatísticas quantitativas relevantes e séries para gráficos.
    Inclui auditoria automática dos trades.
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
    trade_start_index = None
    last_trade_price = None
    trade_durations = []
    trade_pnls = []
    trade_types = []
    trade_dates = []

    for idx, row in joined.iterrows():
        sig = row['shifted_signal']
        open_price = row['open']
        # BUY
        if sig == 1 and position <= 0:
            fee = balance * fee_pct
            balance_after_fee = balance - fee
            position = balance_after_fee / open_price
            trades.append({'dt_entry': idx, 'type': 'BUY', 'price_entry': open_price, 'fee_entry': fee, 'balance_before_entry': balance, 'position_qty': position})
            balance = 0
            trade_start_index = idx
            last_trade_price = open_price
        # SELL
        elif sig == -1 and position > 0:
            gross = position * open_price
            fee = gross * fee_pct
            proceeds = gross - fee
            ret = (proceeds - (trades[-1]['balance_before_entry'] if trades else initial_balance)) / (trades[-1]['balance_before_entry'] if trades else initial_balance)
            trade_returns.append(ret)
            trade_outcomes.append(proceeds > (trades[-1]['balance_before_entry'] if trades else initial_balance))
            trade_duration = joined.index.get_loc(idx) - (joined.index.get_loc(trade_start_index) if trade_start_index is not None else 0)
            trade_durations.append(trade_duration)
            trade_pnls.append(proceeds - (trades[-1]['balance_before_entry'] if trades else initial_balance))
            trade_types.append('LONG')
            trade_dates.append({"entry": trade_start_index, "exit": idx})
            balance = proceeds
            trades[-1].update({'dt_exit': idx, 'price_exit': open_price, 'fee_exit': fee, 'balance_after_exit': balance, 'pnl': proceeds - (trades[-1]['balance_before_entry'] if trades else initial_balance), 'duration': trade_duration})
            position = 0
            trade_start_index = None
            last_trade_price = None
        # equity curve após cada candle
        cur_equity = balance + position * open_price
        equity_curve.append(cur_equity)
    
    # Se posição aberta ao final, liquida
    if position > 0:
        gross = position * joined.iloc[-1]['open']
        fee = gross * fee_pct
        final_balance = gross - fee
        # computar PnL desse trade final
        ret = (final_balance - (trades[-1]['balance_before_entry'] if trades else initial_balance)) / (trades[-1]['balance_before_entry'] if trades else initial_balance)
        trade_returns.append(ret)
        trade_outcomes.append(final_balance > (trades[-1]['balance_before_entry'] if trades else initial_balance))
        trade_duration = len(joined) - (joined.index.get_loc(trade_start_index) if trade_start_index is not None else 0)
        trade_durations.append(trade_duration)
        trade_pnls.append(final_balance - (trades[-1]['balance_before_entry'] if trades else initial_balance))
        trade_types.append('LONG')
        trade_dates.append({"entry": trade_start_index, "exit": joined.index[-1]})
        trades[-1].update({'dt_exit': joined.index[-1], 'price_exit': joined.iloc[-1]['open'], 'fee_exit': fee, 'balance_after_exit': final_balance, 'pnl': final_balance - (trades[-1]['balance_before_entry'] if trades else initial_balance), 'duration': trade_duration})
    else:
        final_balance = balance
    equity_curve = np.array(equity_curve)
    returns = pd.Series(np.diff(equity_curve) / equity_curve[:-1])

    # Drawdown e equity
    max_dd, peak_idx, dd_idx, drawdown_curve = _compute_max_drawdown(equity_curve)
    max_dd_pct = abs(max_dd) * 100
    recov_time = _compute_recovery_time(equity_curve, peak_idx, dd_idx)

    total_return = final_balance - initial_balance
    total_return_pct = (final_balance / initial_balance - 1) * 100

    # Métricas avançadas
    avg_ret_per_trade = np.mean(trade_returns) if trade_returns else 0
    avg_daily_ret = returns.mean() if not returns.empty else 0
    win_rate = (np.sum(trade_outcomes) / len(trade_outcomes)) * 100 if trade_outcomes else 0
    gross_profit = np.sum([r for r in trade_returns if r > 0]) * initial_balance
    gross_loss = -np.sum([r for r in trade_returns if r < 0]) * initial_balance
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else np.inf
    n_trades = len(trade_returns)
    rf = 0
    excess_ret = returns - rf
    sharpe = (excess_ret.mean() / (excess_ret.std() + 1e-9)) * np.sqrt(252) if not returns.empty else np.nan
    volatility = returns.std() * np.sqrt(252) if not returns.empty else np.nan
    net_profit = total_return  # igual ao total_return (pode mudar no futuro)

    # CAGR
    n_days = len(processed_data)
    cagr = _compute_cagr(initial_balance, final_balance, n_days)

    # Tempo médio em posição
    mean_duration = np.mean(trade_durations) if trade_durations else 0

    # Benchmark hold
    benchmark = _get_benchmark_hold_returns(processed_data, initial_balance)

    # Auditoria automática dos trades
    audit_report = None
    try:
        audit_report = audit_trades(trades, verbose=False)
        # Se houver flags de erro, adiciona um alerta simples
        n_flags = 0
        if not audit_report.empty and 'audit_flag' in audit_report:
            n_flags = int(audit_report['audit_flag'].sum())
        audit_summary = {
            "n_trades_flagged": n_flags,
            "audit_flags": audit_report[['dt_entry','dt_exit','pnl','duration','audit_flag']].to_dict(orient="records") if not audit_report.empty else [],
            "audit_message": f"{n_flags} trades com comportamento suspeito detectado." if n_flags > 0 else "Nenhum problema crítico detectado nos trades."
        }
    except Exception as e:
        audit_summary = {
            "n_trades_flagged": -1,
            "audit_flags": [],
            "audit_message": f"Erro na auditoria: {str(e)}"
        }

    return {
        "symbol": symbol,
        "interval": interval,
        "strategy": strategy_name,
        "initial_balance": round(initial_balance, 2),
        "final_balance": round(final_balance, 2),
        "total_return": round(total_return, 2),
        "total_return_pct": round(total_return_pct, 2),
        "net_profit": round(net_profit, 2),
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
        "cagr_pct": round(cagr, 2),
        "trade_fee_pct": fee_pct,
        "mean_trade_duration": round(mean_duration, 2),
        # ---- Detalhamento para gráficos/resultados avançados: ----
        "equity_curve": list(map(float, equity_curve)),
        "drawdown_curve": list(map(float, drawdown_curve)),
        "returns_per_trade": list(map(float, trade_returns)),  # retornos cada trade
        "trade_durations": list(map(int, trade_durations)),    # duração cada trade
        "trade_pnls": list(map(float, trade_pnls)),            # lucro/prejuízo de cada trade
        "trade_types": list(trade_types),
        "trade_dates": trade_dates,
        "trades": trades,
        "benchmark": benchmark,
        # Resultado da auditoria de trades
        "trade_audit": audit_summary
    }

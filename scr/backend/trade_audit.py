import pandas as pd
import numpy as np

def audit_trades(trades, max_pnl_threshold=0.5, max_duration_threshold=60, verbose=True):
    """
    Faz uma auditoria simples na lista de trades do backtest, procurando:
      - PnLs muito altos ou baixos em um único trade (possível bug/dado incoerente)
      - Durations extremamente curtos ou longos
      - Forward bias: Se o trade é aberto e fechado na mesma barra (possível uso incorreto de sinal)
      - Trades com PnL positivo irreal (ex: >50% em um trade) indicando spikes ou vazamentos
    Args:
        trades (list[dict]): Lista retornada pelo backtester (cada trade: dict)
        max_pnl_threshold (float): PnL máximo permitido por trade em proporção ao capital (default=0.5 = 50%)
        max_duration_threshold (int): Duração máxima considerada normal para um trade (em barras/candles)
        verbose (bool): Se True, imprime um resumo
    Returns:
        pd.DataFrame: DataFrame com flag de outliers, para inspeção manual.
    """
    if not trades or len(trades) == 0:
        if verbose:
            print("Nenhum trade para auditar.")
        return pd.DataFrame()
    
    df = pd.DataFrame(trades)
    issues = []

    # Normaliza nomes de colunas (caso estejam diferentes)
    for col in ['pnl', 'duration']:
        if col not in df.columns:
            raise ValueError(f"Coluna obrigatória '{col}' não está presente.")

    # FLAG 1: Trades com PnL acima de max_pnl_threshold (em proporção ao capital de entrada)
    entry_balances = df['balance_before_entry'].replace(0, np.nan).abs()
    df['pnl_pct'] = df['pnl'] / entry_balances
    df['high_pnl'] = df['pnl_pct'].abs() > max_pnl_threshold

    # FLAG 2: Trades com duração muito longa ou zero (riscos de forward/loop bias)
    df['zero_or_short_duration'] = df['duration'] <= 0
    df['long_duration'] = df['duration'] > max_duration_threshold

    # FLAG 3: Entry/Exit em sequência igual
    df['same_entry_exit'] = df['dt_entry'] == df['dt_exit']

    summary = {
        "total_trades": len(df),
        "high_pnl_trades": int(df['high_pnl'].sum()),
        "long_duration_trades": int(df['long_duration'].sum()),
        "zero_or_samebar_trades": int(df['zero_or_short_duration'].sum() + df['same_entry_exit'].sum()),
    }
    if verbose:
        print("=== AUDITORIA DE TRADES ===")
        for k, v in summary.items():
            print(f"{k}: {v}")
        print("Exemplos de trades suspeitos:")
        print(df[df[['high_pnl', 'long_duration', 'zero_or_short_duration', 'same_entry_exit']].any(axis=1)].head())

    df['audit_flag'] = df[['high_pnl', 'long_duration', 'zero_or_short_duration', 'same_entry_exit']].any(axis=1)

    return df

# Exemplo rápido de uso:
if __name__ == "__main__":
    # Simulação fictícia:
    example_trades = [
        {'dt_entry': '2020-01-01', 'dt_exit': '2020-01-02', 'balance_before_entry': 10000, 'pnl': 50, 'duration': 1},   # normal
        {'dt_entry': '2020-01-02', 'dt_exit': '2020-01-02', 'balance_before_entry': 10000, 'pnl': 6000, 'duration': 0}, # suspeito
        {'dt_entry': '2020-01-03', 'dt_exit': '2020-01-10', 'balance_before_entry': 10000, 'pnl': 6000, 'duration': 7}, # suspeito
    ]
    audit_trades(example_trades)
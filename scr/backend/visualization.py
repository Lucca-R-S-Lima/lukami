import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from plotly.subplots import make_subplots
import numpy as np
import matplotlib.pyplot as plt

def plot_results(results):
    """
    Plota os resultados do backtest (versão Matplotlib para compatibilidade)
    """
    plt.figure(figsize=(12, 6))
    
    # Preço e médias móveis
    plt.subplot(2, 1, 1)
    plt.plot(results['price'], label='Preço BTC')
    plt.plot(results['short_ma'], label='Média Curta')
    plt.plot(results['long_ma'], label='Média Longa')
    plt.title('Estratégia de Média Móvel')
    plt.legend()
    
    # Retorno acumulado
    plt.subplot(2, 1, 2)
    plt.plot(results['cumulative_return'], label='Retorno da Estratégia')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig('data/backtest_plot.png')
    plt.show()

def plot_results_plotly(results, trades=None, heatmap_type='pnl'):
    """
    Plota resultados do backtest de forma interativa usando Plotly,
    com linha do equity curve, médias, retorno acumulado e um heatmap customizável.

    Args:
        results (dict): Resultado do backtest.
        trades (list[dict]): Lista de trades (result['trades']). Opcional (pega do results).
        heatmap_type (str): Tipo de heatmap: 'pnl', 'win', 'drawdown', 'bestworst'.
    """
    # --- Prepara dados principais ---
    df = pd.DataFrame({
        'Equity': results.get('cumulative_return', []),
    })
    if 'price' in results:
        df['price'] = results['price']
    if 'short_ma' in results:
        df['Short MA'] = results['short_ma']
    if 'long_ma' in results:
        df['Long MA'] = results['long_ma']
    # Tenta adicionar datas, se estiverem no índice ou como coluna
    if isinstance(results.get('price'), (pd.Series, pd.DataFrame)):
        if hasattr(results['price'], 'index'):
            df.index = results['price'].index

    # --- Layout com subplot para heatmap abaixo ---
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.12,
        row_heights=[0.6, 0.4],
        subplot_titles=("Equity/Preço/Médias móveis", "Heatmap")
    )

    # === Linha principal do topo: Equity curve, preço e médias ===
    fig.add_trace(go.Scatter(
        y=df['Equity'], mode='lines', name='Equity Curve',
        hoverinfo='x+y'
    ), row=1, col=1)
    if 'price' in df:
        fig.add_trace(go.Scatter(
            y=df['price'], mode='lines', name='Preço',
            line=dict(dash='dot'), opacity=0.6
        ), row=1, col=1)
    if 'Short MA' in df:
        fig.add_trace(go.Scatter(
            y=df['Short MA'], mode='lines', name='Média Curta',
            line=dict(dash='dash'), opacity=0.8
        ), row=1, col=1)
    if 'Long MA' in df:
        fig.add_trace(go.Scatter(
            y=df['Long MA'], mode='lines', name='Média Longa',
            line=dict(dash='dot'), opacity=0.8
        ), row=1, col=1)

    # --- Prepara dados para HEATMAP ---
    trades = trades or results.get('trades', [])
    df_trades = pd.DataFrame(trades) if trades else pd.DataFrame()
    if not df_trades.empty:
        # Garantir que existam colunas pasta each heatmap, e o dt_entry seja datetime
        if 'dt_entry' in df_trades.columns and not pd.api.types.is_datetime64_any_dtype(df_trades['dt_entry']):
            df_trades['dt_entry'] = pd.to_datetime(df_trades['dt_entry'], errors='coerce')
            df_trades['date'] = df_trades['dt_entry'].dt.date
    
    heatmap_df = None
    heatmap_title = ""
    hovertemplate = None

    # -- PnL por data (HEATMAP_TYPE = 'pnl') --
    if heatmap_type == 'pnl' and not df_trades.empty and 'pnl' in df_trades.columns:
        grp = df_trades.groupby('date').agg({'pnl': 'sum'})
        heatmap_df = grp.reset_index()
        heatmap_title = "PnL diário"
        hovertemplate = "Data: %{x}<br>PnL: %{z:,.2f}"
    # -- Acertos/erros (HEATMAP_TYPE = 'win') --
    elif heatmap_type == 'win' and not df_trades.empty and 'pnl' in df_trades.columns:
        df_trades['is_win'] = df_trades['pnl'] > 0
        grp = df_trades.groupby('date')['is_win'].mean()
        heatmap_df = grp.reset_index()
        heatmap_title = "Taxa de acerto diário (1=win, 0=loss)"
        hovertemplate = "Data: %{x}<br>Win-rate: %{z:.2%}"
    # -- Drawdown por data (HEATMAP_TYPE = 'drawdown') --
    elif heatmap_type == 'drawdown' and 'drawdown_curve' in results:
        # Para cada dia/índice, mostra drawdown
        dd_curve = results['drawdown_curve']
        dates = None
        if 'price' in results and hasattr(results['price'], 'index'):
            dates = results['price'].index
        else:
            dates = list(range(len(dd_curve)))
        heatmap_df = pd.DataFrame({'date': dates, 'drawdown': dd_curve})
        heatmap_title = "Drawdown diário"
        hovertemplate = "Data: %{x}<br>Drawdown: %{z:.2%}"
    # -- Melhores/piores dias (HEATMAP_TYPE = 'bestworst') --
    elif heatmap_type == 'bestworst' and not df_trades.empty and 'pnl' in df_trades.columns:
        grp = df_trades.groupby('date').agg({'pnl': 'sum'})
        # Colore forte os top 10 e bottom 10
        heatmap_df = grp.reset_index()
        heatmap_df['is_best'] = heatmap_df['pnl'].rank(ascending=False) <= 10
        heatmap_df['is_worst'] = heatmap_df['pnl'].rank(ascending=True) <= 10
        heatmap_title = "Top 10 melhores/piores dias (PnL)"
        hovertemplate = "Data: %{x}<br>PnL: %{z:,.2f}"

    # --- Heatmap rendering ---
    if heatmap_df is not None and not heatmap_df.empty:
        # Heatmap 1D: datas x valor
        fig.add_trace(go.Heatmap(
            x=heatmap_df[heatmap_df.columns[0]],
            y=[""] * heatmap_df.shape[0],
            z=heatmap_df[heatmap_df.columns[-2]] if heatmap_type in ['pnl', 'drawdown', 'win'] else heatmap_df['pnl'],
            colorscale="YlGnBu" if heatmap_type != 'bestworst' else [[0, "crimson"], [0.5, "white"], [1, "darkgreen"]],
            colorbar=dict(title=heatmap_title),
            showscale=True,
            hovertemplate=hovertemplate,
        ), row=2, col=1)
        # Para type bestworst: destaca TOP/BOTTOM
        if heatmap_type == 'bestworst':
            fig.add_trace(go.Scatter(
                x=heatmap_df.loc[heatmap_df['is_best'], 'date'],
                y=[""] * heatmap_df['is_best'].sum(),
                mode='markers',
                marker=dict(size=14, color='green', symbol='star', line=dict(width=2, color='black')),
                name='TOP 10',
                hoverinfo='x+z',
                showlegend=True
            ), row=2, col=1)
            fig.add_trace(go.Scatter(
                x=heatmap_df.loc[heatmap_df['is_worst'], 'date'],
                y=[""] * heatmap_df['is_worst'].sum(),
                mode='markers',
                marker=dict(size=14, color='red', symbol='star', line=dict(width=2, color='black')),
                name='WORST 10',
                hoverinfo='x+z',
                showlegend=True
            ), row=2, col=1)
    else:
        # Vazio, só exemplo de layout
        fig.add_trace(go.Scatter(
            x=[],
            y=[],
        ), row=2, col=1)

    # --- Layout e interação ---
    fig.update_layout(
        height=750,
        title="Resultados do Backtest — Interativo",
        legend_title_text="Séries",
        hovermode='x unified',
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.1,
                xanchor="left",
                y=1.15,
                yanchor="top",
                buttons=list([
                    {"label": "Heatmap: PnL", "method": "update", "args": [{"visible": [True, True, True, True, True]}, {"annotations": [{"text": "PnL diário"}]}], "args2": []},
                ])
            ),
            dict(
                type="dropdown",
                x=0.5,
                xanchor="center",
                y=1.15,
                yanchor="top",
                buttons=[
                    dict(
                        args=[{'visible': [True]*len(fig.data)}],
                        label='Equity & Todos',
                        method='update'
                    ),
                    dict(
                        args=[{'visible': [True, True, True, False, False, False]}],
                        label='Apenas Equity/Preço/MAs',
                        method='update'
                    ),
                ]
            )
        ]
    )
    
    # Salvar como HTML interativo e mostrar
    fig.write_html('data/backtest_interactive.html')
    fig.show()

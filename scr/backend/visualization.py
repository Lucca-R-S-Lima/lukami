import matplotlib.pyplot as plt
import pandas as pd

def plot_results(results):
    """
    Plota os resultados do backtest
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

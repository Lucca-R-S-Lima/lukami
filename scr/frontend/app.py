
import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, 
    QLineEdit, QMessageBox, QFrame, QDateEdit, QSizePolicy, QScrollArea
)
from PySide6.QtCore import Qt, Signal, Slot, QDate
from PySide6.QtGui import QIcon, QFont

# Gráficos
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

# --- Configuração de caminhos para importação do backend ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.backtest_service import run_backtest, get_available_strategies, get_available_intervals
from backend.data_handlers.binance_data import BinanceDataHandler

class SidebarButton(QPushButton):
    """Botão personalizado para a barra lateral"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(50)
        self.setCheckable(True)
        self.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 10px;
                border: none;
                border-radius: 5px;
                background-color: transparent;
                color: #FFFFFF;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QPushButton:checked {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)

class Sidebar(QWidget):
    """Barra lateral de navegação"""
    pageChanged = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumWidth(200)
        self.setMinimumWidth(200)
        self.setStyleSheet("background-color: #2C3E50;")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(10)
        
        title = QLabel("Backtest Financeiro")
        title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #34495E;")
        layout.addWidget(separator)
        layout.addSpacing(20)
        
        self.homeBtn = SidebarButton("Início")
        self.homeBtn.setChecked(True)
        self.homeBtn.clicked.connect(lambda: self.changePage(0))
        
        self.resultsBtn = SidebarButton("Resultados")
        self.resultsBtn.clicked.connect(lambda: self.changePage(1))
        
        self.settingsBtn = SidebarButton("Configurações")
        self.settingsBtn.clicked.connect(lambda: self.changePage(2))
        
        layout.addWidget(self.homeBtn)
        layout.addWidget(self.resultsBtn)
        layout.addWidget(self.settingsBtn)
        layout.addStretch()
        
        self.helpBtn = SidebarButton("Ajuda")
        self.helpBtn.clicked.connect(self.showHelp)
        layout.addWidget(self.helpBtn)
        self.setLayout(layout)
        self.buttons = [self.homeBtn, self.resultsBtn, self.settingsBtn]
    
    def changePage(self, index):
        for i, btn in enumerate(self.buttons):
            btn.setChecked(i == index)
        self.pageChanged.emit(index)
    
    def showHelp(self):
        QMessageBox.information(
            self, 
            "Ajuda", 
            "Sistema de Backtesting Financeiro\n\n"
            "Este aplicativo permite testar estratégias de trading em dados históricos.\n\n"
            "Para começar, selecione uma estratégia e um intervalo de tempo na página inicial."
        )

class HomeWidget(QWidget):
    """Página inicial com configurações de backtest"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parentWindow = parent  # Para acessar MainWindow (para navegação e integração)
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Configuração de Backtest")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)
        
        description = QLabel("Configure os parâmetros para executar o backtest da estratégia.")
        description.setWordWrap(True)
        layout.addWidget(description)
        layout.addSpacing(10)

        self.strategies = get_available_strategies()
        self.strategy_cb = QComboBox()
        self.strategy_cb.addItems(self.strategies)
        self.strategy_cb.currentTextChanged.connect(self.update_params_visibility)
        layout.addWidget(QLabel("Estratégia:"))
        layout.addWidget(self.strategy_cb)

        self.intervals = get_available_intervals()
        self.interval_cb = QComboBox()
        self.interval_cb.addItems(self.intervals)
        layout.addWidget(QLabel("Intervalo:"))
        layout.addWidget(self.interval_cb)
        
        self.symbols = [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT",
            "MATICUSDT", "XRPUSDT", "DOTUSDT", "DOGEUSDT", "LTCUSDT"
        ]
        self.symbol_cb = QComboBox()
        self.symbol_cb.addItems(self.symbols)
        self.symbol_cb.currentTextChanged.connect(self.check_symbol_data)
        layout.addWidget(QLabel("Símbolo:"))
        layout.addWidget(self.symbol_cb)
        
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate(2020, 1, 1))
        layout.addWidget(QLabel("Data inicial:"))
        layout.addWidget(self.start_date_edit)
        
        self.balance_line = QLineEdit()
        self.balance_line.setPlaceholderText("10000")
        self.balance_line.setText("10000")
        layout.addWidget(QLabel("Saldo inicial:"))
        layout.addWidget(self.balance_line)

        self.params_frame = QFrame()
        params_layout = QVBoxLayout(self.params_frame)
        self.short_line = QLineEdit()
        self.short_line.setPlaceholderText("10")
        self.short_line.setText("10")
        params_layout.addWidget(QLabel("Janela curta:"))
        params_layout.addWidget(self.short_line)
        self.long_line = QLineEdit()
        self.long_line.setPlaceholderText("30")
        self.long_line.setText("30")
        params_layout.addWidget(QLabel("Janela longa:"))
        params_layout.addWidget(self.long_line)
        layout.addWidget(QLabel("Parâmetros da estratégia:"))
        layout.addWidget(self.params_frame)

        self.fee_line = QLineEdit()
        self.fee_line.setPlaceholderText("0.1")
        self.fee_line.setText("0.1")
        layout.addWidget(QLabel("Taxa de trading (%):"))
        layout.addWidget(self.fee_line)

        layout.addSpacing(20)
        
        self.start_btn = QPushButton("Executar Backtest")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498DB;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
            QPushButton:pressed {
                background-color: #1F618D;
            }
        """)
        self.start_btn.setMinimumHeight(40)
        self.start_btn.clicked.connect(self.run_backtest)
        layout.addWidget(self.start_btn)

        self.result_label = QLabel()
        self.result_label.setWordWrap(True)
        self.result_label.setTextFormat(Qt.RichText)
        layout.addWidget(self.result_label)
        layout.addStretch()
        self.setLayout(layout)
        self.update_params_visibility()

    def update_params_visibility(self):
        strategy = self.strategy_cb.currentText()
        if "MovingAverage" in strategy:
            self.params_frame.setVisible(True)
        else:
            self.params_frame.setVisible(False)
            
    def check_symbol_data(self, symbol):
        if not symbol:
            return
        interval = self.interval_cb.currentText()
        qdate = self.start_date_edit.date()
        months = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
        ]
        start_date = f"{qdate.day()} {months[qdate.month()-1]} {qdate.year()}"
        if symbol == "SOLUSDT":
            resp = QMessageBox.question(
                self,
                "Dados não encontrados",
                f"Não há dados históricos para {symbol} no intervalo {interval}.\nDeseja baixar agora?",
                QMessageBox.Yes | QMessageBox.No
            )
            if resp == QMessageBox.Yes:
                self.result_label.setText("<span style='color:blue;'>Baixando dados históricos. Aguarde alguns instantes...</span>")
                self.repaint()
                try:
                    handler = BinanceDataHandler()
                    handler.download_all_intervals(symbol=symbol, intervals=[interval], start_date=start_date)
                    self.result_label.setText("<span style='color:green;'>Download concluído! Você já pode executar o backtest.</span>")
                except Exception as e:
                    QMessageBox.critical(self, "Erro", f"Erro ao baixar os dados: {str(e)}")
                    self.result_label.setText("")

    def run_backtest(self):
        strategy = self.strategy_cb.currentText()
        interval = self.interval_cb.currentText()
        symbol = self.symbol_cb.currentText()
        qdate = self.start_date_edit.date()
        months = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
        ]
        start_date = f"{qdate.day()} {months[qdate.month()-1]} {qdate.year()}"
        try:
            initial_balance = float(self.balance_line.text() or "10000")
        except ValueError:
            QMessageBox.warning(self, "Erro", "O saldo inicial deve ser um número válido.")
            return
        params = {}
        if "MovingAverage" in strategy:
            try:
                short = int(self.short_line.text() or "10")
                long = int(self.long_line.text() or "30")
                params = {"short_window": short, "long_window": long}
            except ValueError:
                QMessageBox.warning(self, "Erro", "Os parâmetros da janela devem ser números inteiros.")
                return
        fee_txt = self.fee_line.text().replace(",", ".") or "0.1"
        try:
            fee_pct = float(fee_txt) / 100
        except ValueError:
            QMessageBox.warning(self, "Erro", "A taxa (fee) deve ser um número válido.")
            return
        try:
            result = run_backtest(
                strategy_name=strategy,
                interval=interval,
                symbol=symbol,
                start_date=start_date,
                initial_balance=initial_balance,
                strategy_params=params,
                fee_pct=fee_pct
            )
            if "error" in result and "dados" in result["error"].lower():
                resp = QMessageBox.question(
                    self,
                    "Dados não encontrados",
                    f"Não há dados históricos para {symbol} no intervalo {interval}.\nDeseja baixar agora?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if resp == QMessageBox.Yes:
                    self.result_label.setText("<span style='color:blue;'>Baixando dados históricos. Aguarde alguns instantes...</span>")
                    self.repaint()
                    try:
                        handler = BinanceDataHandler()
                        handler.download_all_intervals(symbol=symbol, intervals=[interval], start_date=start_date)
                        self.result_label.setText("<span style='color:green;'>Download concluído! Executando o backtest...</span>")
                        self.repaint()
                        result = run_backtest(
                            strategy_name=strategy,
                            interval=interval,
                            symbol=symbol,
                            start_date=start_date,
                            initial_balance=initial_balance,
                            strategy_params=params,
                            fee_pct=fee_pct
                        )
                    except Exception as e:
                        QMessageBox.critical(self, "Erro", f"Erro ao baixar os dados: {str(e)}")
                        self.result_label.setText("")
                        return
                else:
                    self.result_label.setText("<span style='color:orange;'>Execução cancelada: Dados históricos não disponíveis.</span>")
                    return
            if "error" in result:
                self.result_label.setText(f"<b style='color:red;'>Erro: {result['error']}</b>")
            else:
                res = result
                html = f'''
                <hr>
                <h3>Resumo Rápido:</h3>
                <b>Lucro Total:</b> {res['total_return']:.2f} ({res['total_return_pct']:.2f}%)<br>
                <b>Retorno médio por trade:</b> {res['avg_return_per_trade']:.2f}%<br>
                <b>Máx. Drawdown:</b> {res['max_drawdown_value']:.2f} ({res['max_drawdown_pct']:.2f}%)<br>
                <b>Nº operações:</b> {res['n_trades']}<br>
                <b>Sharpe Ratio:</b> {res['sharpe_ratio']}<br>
                '''
                self.result_label.setText(html)
                # Integração com ResultsWidget e navegação
                if self.parentWindow:
                    self.parentWindow.latest_result = res
                    self.parentWindow.results_page.set_results(res)
                    self.parentWindow.change_page(1)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro ao executar o backtest: {str(e)}")

# -------------------- ResultsWidget detalhado --------------------
class ResultsWidget(QWidget):
    """Página de resultados detalhados: métricas + todos os gráficos"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.raw_result = None
        self._init_layout()
    
    def _init_layout(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        self.metrics_label = QLabel("Execute um backtest para ver resultados.")
        self.metrics_label.setWordWrap(True)
        layout.addWidget(self.metrics_label)

        self.graphs_area = QVBoxLayout()
        layout.addLayout(self.graphs_area)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container.setLayout(layout)
        scroll.setWidget(container)
        scroll_layout = QVBoxLayout(self)
        scroll_layout.addWidget(scroll)
        self.setLayout(scroll_layout)

    def clear_graphs(self):
        while self.graphs_area.count():
            item = self.graphs_area.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

    def set_results(self, result):
        self.raw_result = result
        self.clear_graphs()
        if not result or "error" in result:
            self.metrics_label.setText(
                "<b style='color:red;'>Nenhum resultado de backtest disponível.</b>"
            )
            return
        metrics = f"""
        <h2>📈 Principais Métricas</h2>
        <ul>
            <li><b>Lucro Total:</b> {result['total_return']:.2f} ({result['total_return_pct']:.2f}%)</li>
            <li><b>Lucro Líquido:</b> {result['net_profit']:.2f}</li>
            <li><b>CAGR:</b> {result['cagr_pct']:.2f}%</li>
            <li><b>Max Drawdown:</b> {result['max_drawdown_value']:.2f} ({result['max_drawdown_pct']:.2f}%)</li>
            <li><b>Sharpe Ratio:</b> {result['sharpe_ratio']}</li>
            <li><b>Taxa de acerto:</b> {result['win_rate_pct']:.2f}%</li>
            <li><b>Expectativa por trade:</b> {result['avg_return_per_trade']:.2f}%</li>
            <li><b>Número total de Trades:</b> {result['n_trades']}</li>
            <li><b>Profit Factor:</b> {result['profit_factor']}</li>
            <li><b>Tempo médio em posição:</b> {result['mean_trade_duration']:.2f} períodos</li>
            <li><b>Volatilidade anualizada:</b> {result['volatility_pct']}%</li>
        </ul>
        <h3>🏁 Benchmark Buy&Hold: {result['benchmark']['total_return']:.2f} ({result['benchmark']['total_return_pct']:.2f}%)</h3>
        """
        self.metrics_label.setText(metrics)
        # Gráfico 1: Equity Curve + Benchmark
        fig1, ax1 = plt.subplots(figsize=(7, 3))
        ax1.plot(result['equity_curve'], label="Equity Curve", linewidth=2)
        ax1.plot(result['benchmark']['equity_curve'], label="Buy&Hold", linestyle='--', color='gray')
        ax1.set_title("Equity Curve vs. Benchmark")
        ax1.set_ylabel("Saldo")
        ax1.set_xlabel("Período")
        ax1.legend()
        self._add_canvas(fig1)
        # Gráfico 2: Drawdown Curve
        fig2, ax2 = plt.subplots(figsize=(7, 2.5))
        ax2.plot(result['drawdown_curve'], color='red')
        ax2.set_title("Curva de Drawdown")
        ax2.set_ylabel("Drawdown (%)")
        ax2.set_xlabel("Período")
        self._add_canvas(fig2)
        # Gráfico 3: Histograma de Retornos por Trade
        fig3, ax3 = plt.subplots(figsize=(6, 2.5))
        ax3.hist(result['returns_per_trade'], bins=20, color="#3399DD", edgecolor="#333")
        ax3.set_title("Retornos por Trade (%)")
        ax3.set_xlabel("Return")
        ax3.set_ylabel("Frequência")
        self._add_canvas(fig3)
        # Gráfico 4: Histograma de Duração dos Trades
        fig4, ax4 = plt.subplots(figsize=(6, 2.5))
        ax4.hist(result['trade_durations'], bins=20, color="#77CF77", edgecolor="#333")
        ax4.set_title("Distribuição da Duração dos Trades")
        ax4.set_xlabel("Períodos")
        ax4.set_ylabel("Frequência")
        self._add_canvas(fig4)
        # Gráfico 5: Scatterplot: Retorno vs. Duração dos Trades
        fig5, ax5 = plt.subplots(figsize=(6, 2.5))
        ax5.scatter(result['trade_durations'], result['returns_per_trade'], alpha=0.6)
        ax5.set_title("Retorno vs. Duração do Trade")
        ax5.set_xlabel("Duração (períodos)")
        ax5.set_ylabel("Retorno (%)")
        self._add_canvas(fig5)

    def _add_canvas(self, fig):
        canvas = FigureCanvas(fig)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        canvas.updateGeometry()
        self.graphs_area.addWidget(canvas)

class SettingsWidget(QWidget):
    """Página de configurações"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        title = QLabel("Configurações")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)
        layout.addWidget(QLabel("Esta página permitirá configurar parâmetros globais do sistema."))
        layout.addWidget(QLabel("Funcionalidade em desenvolvimento."))
        layout.addStretch()
        self.setLayout(layout)

class MainWindow(QMainWindow):
    """Janela principal da aplicação"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Backtesting Financeiro")
        self.setMinimumSize(900, 600)
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.sidebar = Sidebar()
        self.sidebar.pageChanged.connect(self.change_page)
        self.page_stack = QStackedWidget()
        self.results_page = ResultsWidget()
        self.home_page = HomeWidget(self)
        self.settings_page = SettingsWidget()
        self.page_stack.addWidget(self.home_page)
        self.page_stack.addWidget(self.results_page)
        self.page_stack.addWidget(self.settings_page)
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.page_stack)
        self.setCentralWidget(central_widget)
        self.latest_result = None

        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #F5F5F5;
                color: #333333;
                font-family: Arial, sans-serif;
            }
            QLabel {
                color: #333333;
            }
            QComboBox, QLineEdit, QDateEdit {
                padding: 8px;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                background-color: white;
            }
            QComboBox:focus, QLineEdit:focus, QDateEdit:focus {
                border: 1px solid #3498DB;
            }
        """)

    @Slot(int)
    def change_page(self, index):
        self.page_stack.setCurrentIndex(index)
        if index == 1 and self.latest_result is not None:
            self.results_page.set_results(self.latest_result)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

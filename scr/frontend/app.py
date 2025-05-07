import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, 
    QLineEdit, QMessageBox, QFrame, QDateEdit
)
from PySide6.QtCore import Qt, Signal, Slot, QDate
from PySide6.QtGui import QIcon, QFont

# --- Configuração de caminhos para importação do backend ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# IMPORTAÇÕES REAIS do backend!
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
        
        # Estilo da barra lateral
        self.setStyleSheet("background-color: #2C3E50;")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(10)
        
        # Título da aplicação
        title = QLabel("Backtest Financeiro")
        title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #34495E;")
        layout.addWidget(separator)
        layout.addSpacing(20)
        
        # Botões de navegação
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
        
        # Espaçador para empurrar o botão de ajuda para baixo
        layout.addStretch()
        
        # Botão de ajuda
        self.helpBtn = SidebarButton("Ajuda")
        self.helpBtn.clicked.connect(self.showHelp)
        layout.addWidget(self.helpBtn)
        
        self.setLayout(layout)
        self.buttons = [self.homeBtn, self.resultsBtn, self.settingsBtn]
    
    def changePage(self, index):
        # Atualiza o estado dos botões
        for i, btn in enumerate(self.buttons):
            btn.setChecked(i == index)
        
        # Emite o sinal para mudar a página
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
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Título da página
        title = QLabel("Configuração de Backtest")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)
        
        # Descrição
        description = QLabel("Configure os parâmetros para executar o backtest da estratégia.")
        description.setWordWrap(True)
        layout.addWidget(description)
        layout.addSpacing(10)

        # ComboBox de estratégias
        self.strategies = get_available_strategies()
        self.strategy_cb = QComboBox()
        self.strategy_cb.addItems(self.strategies)
        self.strategy_cb.currentTextChanged.connect(self.update_params_visibility)
        layout.addWidget(QLabel("Estratégia:"))
        layout.addWidget(self.strategy_cb)

        # ComboBox de intervalos
        self.intervals = get_available_intervals()
        self.interval_cb = QComboBox()
        self.interval_cb.addItems(self.intervals)
        layout.addWidget(QLabel("Intervalo:"))
        layout.addWidget(self.interval_cb)
        
        # Símbolo (ComboBox)
        self.symbols = [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT",
            "MATICUSDT", "XRPUSDT", "DOTUSDT", "DOGEUSDT", "LTCUSDT"
        ]
        self.symbol_cb = QComboBox()
        self.symbol_cb.addItems(self.symbols)
        self.symbol_cb.currentTextChanged.connect(self.check_symbol_data)
        layout.addWidget(QLabel("Símbolo:"))
        layout.addWidget(self.symbol_cb)
        
        # Data inicial (DateEdit com calendário)
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate(2020, 1, 1))
        layout.addWidget(QLabel("Data inicial:"))
        layout.addWidget(self.start_date_edit)
        
        # Saldo inicial
        self.balance_line = QLineEdit()
        self.balance_line.setPlaceholderText("10000")
        self.balance_line.setText("10000")
        layout.addWidget(QLabel("Saldo inicial:"))
        layout.addWidget(self.balance_line)

        # Parâmetros específicos (Moving Average)
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

        # Taxa (fee)
        self.fee_line = QLineEdit()
        self.fee_line.setPlaceholderText("0.1")
        self.fee_line.setText("0.1")
        layout.addWidget(QLabel("Taxa de trading (%):"))
        layout.addWidget(self.fee_line)

        layout.addSpacing(20)
        
        # Botão de execução
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

        # Resultados
        self.result_label = QLabel()
        self.result_label.setWordWrap(True)
        self.result_label.setTextFormat(Qt.RichText)
        layout.addWidget(self.result_label)
        
        # Espaçador para empurrar tudo para cima
        layout.addStretch()

        self.setLayout(layout)
        self.update_params_visibility()

    def update_params_visibility(self):
        """Atualiza a visibilidade dos parâmetros com base na estratégia selecionada"""
        strategy = self.strategy_cb.currentText()
        
        # Por enquanto, só temos parâmetros para MovingAverage
        if "MovingAverage" in strategy:
            self.params_frame.setVisible(True)
        else:
            self.params_frame.setVisible(False)
            
    def check_symbol_data(self, symbol):
        """Verifica se existem dados para o símbolo selecionado e oferece download se necessário"""
        if not symbol:
            return
            
        interval = self.interval_cb.currentText()
        qdate = self.start_date_edit.date()
        months = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
        ]
        start_date = f"{qdate.day()} {months[qdate.month()-1]} {qdate.year()}"
        
        # Simulação de verificação de dados (em produção, isso chamaria uma função real do backend)
        # Para fins de demonstração, vamos simular que SOLUSDT não tem dados
        if symbol == "SOLUSDT":
            resp = QMessageBox.question(
                self,
                "Dados não encontrados",
                f"Não há dados históricos para {symbol} no intervalo {interval}.\nDeseja baixar agora?",
                QMessageBox.Yes | QMessageBox.No
            )
            if resp == QMessageBox.Yes:
                self.result_label.setText("<span style='color:blue;'>Baixando dados históricos. Aguarde alguns instantes...</span>")
                self.repaint()  # Força atualização da UI
                try:
                    handler = BinanceDataHandler()
                    handler.download_all_intervals(symbol=symbol, intervals=[interval], start_date=start_date)
                    self.result_label.setText("<span style='color:green;'>Download concluído! Você já pode executar o backtest.</span>")
                except Exception as e:
                    QMessageBox.critical(self, "Erro", f"Erro ao baixar os dados: {str(e)}")
                    self.result_label.setText("")

    def run_backtest(self):
        """Executa o backtest com os parâmetros configurados"""
        strategy = self.strategy_cb.currentText()
        interval = self.interval_cb.currentText()
        symbol = self.symbol_cb.currentText()
        
        # Converte a data para string no formato 'D MMM YYYY', ex: '1 Jan 2020'
        qdate = self.start_date_edit.date()
        months = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
        ]
        start_date = f"{qdate.day()} {months[qdate.month()-1]} {qdate.year()}"
        
        # Validação do saldo inicial
        try:
            initial_balance = float(self.balance_line.text() or "10000")
        except ValueError:
            QMessageBox.warning(self, "Erro", "O saldo inicial deve ser um número válido.")
            return
        
        # Parâmetros específicos da estratégia
        params = {}
        if "MovingAverage" in strategy:
            try:
                short = int(self.short_line.text() or "10")
                long = int(self.long_line.text() or "30")
                params = {"short_window": short, "long_window": long}
            except ValueError:
                QMessageBox.warning(self, "Erro", "Os parâmetros da janela devem ser números inteiros.")
                return
        
        # Taxa (fee)
        fee_txt = self.fee_line.text().replace(",", ".") or "0.1"
        try:
            fee_pct = float(fee_txt) / 100
        except ValueError:
            QMessageBox.warning(self, "Erro", "A taxa (fee) deve ser um número válido.")
            return

        # Chama o backend
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
            
            # Verifica se há erro de dados ausentes
            if "error" in result and "dados" in result["error"].lower():
                resp = QMessageBox.question(
                    self,
                    "Dados não encontrados",
                    f"Não há dados históricos para {symbol} no intervalo {interval}.\nDeseja baixar agora?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if resp == QMessageBox.Yes:
                    self.result_label.setText("<span style='color:blue;'>Baixando dados históricos. Aguarde alguns instantes...</span>")
                    self.repaint()  # Força atualização da UI
                    try:
                        handler = BinanceDataHandler()
                        handler.download_all_intervals(symbol=symbol, intervals=[interval], start_date=start_date)
                        self.result_label.setText("<span style='color:green;'>Download concluído! Executando o backtest...</span>")
                        self.repaint()  # Força atualização da UI
                        
                        # Tenta executar o backtest novamente
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
                # Renderiza as métricas principais em HTML
                res = result
                html = f"""
                <hr>
                <h3>Resultado do Backtest:</h3>
                <b>Lucro Total:</b> {res['total_return']:.2f} ({res['total_return_pct']:.2f}%)<br>
                <b>Retorno médio por trade:</b> {res['avg_return_per_trade']:.2f}%<br>
                <b>Retorno médio diário:</b> {res['avg_daily_return']:.2f}%<br>
                <b>Máx. Drawdown:</b> {res['max_drawdown_value']:.2f} ({res['max_drawdown_pct']:.2f}%)<br>
                <b>Tempo de recuperação:</b> {res['recovery_time_periods'] if res['recovery_time_periods'] is not None else 'N/A'} períodos<br>
                <b>Taxa de acerto:</b> {res['win_rate_pct']:.2f}%<br>
                <b>Profit Factor:</b> {res['profit_factor']}<br>
                <b>Nº operações:</b> {res['n_trades']}<br>
                <b>Sharpe Ratio:</b> {res['sharpe_ratio']}<br>
                <b>Volatilidade anualizada:</b> {res['volatility_pct']}%<br>
                """
                self.result_label.setText(html)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro ao executar o backtest: {str(e)}")

class ResultsWidget(QWidget):
    """Página de resultados detalhados"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Resultados Detalhados")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)
        
        # Placeholder para resultados futuros
        layout.addWidget(QLabel("Esta página mostrará gráficos e análises detalhadas dos backtests."))
        layout.addWidget(QLabel("Funcionalidade em desenvolvimento."))
        
        layout.addStretch()
        self.setLayout(layout)

class SettingsWidget(QWidget):
    """Página de configurações"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Configurações")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)
        
        # Placeholder para configurações futuras
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
        
        # Widget central com layout horizontal
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Barra lateral
        self.sidebar = Sidebar()
        self.sidebar.pageChanged.connect(self.change_page)
        
        # Stack de páginas
        self.page_stack = QStackedWidget()
        self.home_page = HomeWidget()
        self.results_page = ResultsWidget()
        self.settings_page = SettingsWidget()
        
        self.page_stack.addWidget(self.home_page)
        self.page_stack.addWidget(self.results_page)
        self.page_stack.addWidget(self.settings_page)
        
        # Adiciona widgets ao layout principal
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.page_stack)
        
        self.setCentralWidget(central_widget)
        
        # Estilo global
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
        """Muda a página atual no stack"""
        self.page_stack.setCurrentIndex(index)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

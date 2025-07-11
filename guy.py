import sys
import logging
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton,
                            QTableWidget, QTableWidgetItem, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from api_client import ArkhamClient
from bot_logic import TradingBot

class BotWorker(QThread):
    error = pyqtSignal(str)
    
    def __init__(self, bot, params):
        super().__init__()
        self.bot = bot
        self.params = params
        
    def run(self):
        try:
            self.bot.start(**self.params)
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api = ArkhamClient()
        self.bot = TradingBot()
        self.bot_thread = None
        
        self.setWindowTitle("Arkham Exchange Trading Bot")
        self.setMinimumSize(800, 600)
        
        self.init_ui()
        self.load_trading_pairs()
        self.update_balances()
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Trading pair selection
        pair_layout = QHBoxLayout()
        pair_layout.addWidget(QLabel("Trading Pair:"))
        self.pair_combo = QComboBox()
        pair_layout.addWidget(self.pair_combo)
        layout.addLayout(pair_layout)
        
        # Parameters input
        params_layout = QVBoxLayout()
        
        # USDT Amount
        usdt_layout = QHBoxLayout()
        usdt_layout.addWidget(QLabel("USDT Amount:"))
        self.usdt_input = QLineEdit()
        usdt_layout.addWidget(self.usdt_input)
        params_layout.addLayout(usdt_layout)
        
        # Number of orders
        orders_layout = QHBoxLayout()
        orders_layout.addWidget(QLabel("Number of Orders:"))
        self.orders_input = QLineEdit()
        orders_layout.addWidget(self.orders_input)
        params_layout.addLayout(orders_layout)
        
        # Price drop percentage
        drop_layout = QHBoxLayout()
        drop_layout.addWidget(QLabel("Price Drop %:"))
        self.drop_input = QLineEdit()
        drop_layout.addWidget(self.drop_input)
        params_layout.addLayout(drop_layout)
        
        # First order offset
        offset_layout = QHBoxLayout()
        offset_layout.addWidget(QLabel("First Order Offset %:"))
        self.offset_input = QLineEdit()
        offset_layout.addWidget(self.offset_input)
        params_layout.addLayout(offset_layout)
        
        # Target profit
        profit_layout = QHBoxLayout()
        profit_layout.addWidget(QLabel("Target Profit %:"))
        self.profit_input = QLineEdit()
        profit_layout.addWidget(self.profit_input)
        params_layout.addLayout(profit_layout)
        
        # Price deviation for grid adjustment
        deviation_layout = QHBoxLayout()
        deviation_layout.addWidget(QLabel("Price Deviation %:"))
        self.deviation_input = QLineEdit()
        deviation_layout.addWidget(self.deviation_input)
        params_layout.addLayout(deviation_layout)
        
        layout.addLayout(params_layout)
        
        # Control buttons
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Bot")
        self.start_button.clicked.connect(self.start_bot)
        self.stop_button = QPushButton("Stop Bot")
        self.stop_button.clicked.connect(self.stop_bot)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        layout.addLayout(button_layout)
        
        # Status display
        self.status_label = QLabel("Bot Status: Stopped")
        layout.addWidget(self.status_label)
        
        # Balance table
        self.balance_table = QTableWidget()
        self.balance_table.setColumnCount(3)
        self.balance_table.setHorizontalHeaderLabels(["Asset", "Total", "Available"])
        layout.addWidget(self.balance_table)
        
    def load_trading_pairs(self):
        pairs = self.api.get_trading_pairs()
        for pair in pairs:
            if pair['quoteSymbol'] == 'USDT':
                self.pair_combo.addItem(pair['symbol'])
                
    def update_balances(self):
        balances = self.api.get_balances()
        self.balance_table.setRowCount(len(balances))
        
        for i, balance in enumerate(balances):
            self.balance_table.setItem(i, 0, QTableWidgetItem(balance['symbol']))
            self.balance_table.setItem(i, 1, QTableWidgetItem(balance['balance']))
            self.balance_table.setItem(i, 2, QTableWidgetItem(balance['free']))
            
    def start_bot(self):
        try:
            params = {
                'symbol': self.pair_combo.currentText(),
                'usdt_amount': float(self.usdt_input.text()),
                'num_orders': int(self.orders_input.text()),
                'price_drop': float(self.drop_input.text()),
                'first_order_offset': float(self.offset_input.text()),
                'target_profit_pct': float(self.profit_input.text()),
                'price_deviation_pct': float(self.deviation_input.text())
            }
            
            self.bot_thread = BotWorker(self.bot, params)
            self.bot_thread.error.connect(self.handle_error)
            self.bot_thread.start()
            
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.status_label.setText("Bot Status: Running")
            
        except ValueError as e:
            QMessageBox.warning(self, "Input Error", "Please check your input values")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start bot: {str(e)}")
            
    def stop_bot(self):
        if self.bot_thread and self.bot_thread.isRunning():
            self.bot.stop()
            self.bot_thread.wait()
            
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("Bot Status: Stopped")
        
    def handle_error(self, error_msg):
        QMessageBox.critical(self, "Bot Error", error_msg)
        self.stop_bot()
        
    def closeEvent(self, event):
        self.stop_bot()
        event.accept()

def main():
    logging.basicConfig(level=logging.INFO)
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
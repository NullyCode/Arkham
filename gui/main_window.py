import logging
import time
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QCheckBox
)
from PyQt6.QtCore import QTimer

from api.market_api import get_trading_pairs
from api.trading_api import get_active_orders, get_order_history, get_balances
from gui.bot_worker import BotWorker

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.bot_thread = None
        self.logger = logging.getLogger(__name__)
        self.init_ui()
        self.load_trading_pairs()
        
        # Set up update timers
        self.balance_timer = QTimer()
        self.balance_timer.timeout.connect(self.update_balances)
        self.balance_timer.start(10000)  # Update every 10 seconds
        
        self.orders_timer = QTimer()
        self.orders_timer.timeout.connect(self.update_orders)
        self.orders_timer.start(5000)  # Update every 5 seconds
        
        # Initial updates
        self.update_balances()
        self.update_orders()

    def init_ui(self):
        self.logger.info("Initializing UI...")
        self.setWindowTitle("Arkham Exchange Trading Bot")
        self.setMinimumSize(1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Trading pair selection
        pair_layout = QHBoxLayout()
        pair_layout.addWidget(QLabel("Trading Pair:"))
        self.pair_combo = QComboBox()
        self.pair_combo.currentTextChanged.connect(self.update_orders)
        pair_layout.addWidget(self.pair_combo)
        layout.addLayout(pair_layout)

        # Bot mode selection
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Bot Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Grid Trading", "Volume Trading"])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        layout.addLayout(mode_layout)
        
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
        
        # Target profit (only for Grid Trading)
        self.profit_layout = QHBoxLayout()
        self.profit_layout.addWidget(QLabel("Target Profit %:"))
        self.profit_input = QLineEdit()
        self.profit_layout.addWidget(self.profit_input)
        params_layout.addLayout(self.profit_layout)
        
        # Price deviation (for both modes)
        self.deviation_layout = QHBoxLayout()
        self.deviation_layout.addWidget(QLabel("Price Deviation %:"))
        self.deviation_input = QLineEdit()
        self.deviation_layout.addWidget(self.deviation_input)
        params_layout.addLayout(self.deviation_layout)

        # Trailing limit sell checkbox (only for Volume Trading)
        self.trailing_layout = QHBoxLayout()
        self.trailing_checkbox = QCheckBox("Use Trailing Limit Sell")
        self.trailing_layout.addWidget(self.trailing_checkbox)
        params_layout.addLayout(self.trailing_layout)

        # Delay range (only for Volume Trading)
        self.delay_layout = QHBoxLayout()
        self.delay_layout.addWidget(QLabel("Delay Range (seconds):"))
        self.min_delay_input = QLineEdit()
        self.min_delay_input.setPlaceholderText("Min")
        self.delay_layout.addWidget(self.min_delay_input)
        self.max_delay_input = QLineEdit()
        self.max_delay_input.setPlaceholderText("Max")
        self.delay_layout.addWidget(self.max_delay_input)
        params_layout.addLayout(self.delay_layout)

        # Current delay display (only for Volume Trading)
        self.current_delay_layout = QHBoxLayout()
        self.current_delay_layout.addWidget(QLabel("Current Delay:"))
        self.current_delay_label = QLabel("Not active")
        self.current_delay_layout.addWidget(self.current_delay_label)
        params_layout.addLayout(self.current_delay_layout)
        
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
        
        # Create tables layout
        tables_layout = QHBoxLayout()
        
        # Balance table
        balance_layout = QVBoxLayout()
        balance_layout.addWidget(QLabel("Balances:"))
        self.balance_table = QTableWidget()
        self.balance_table.setColumnCount(3)
        self.balance_table.setHorizontalHeaderLabels(["Asset", "Total", "Available"])
        balance_layout.addWidget(self.balance_table)
        tables_layout.addLayout(balance_layout)
        
        # Active orders table
        active_orders_layout = QVBoxLayout()
        active_orders_layout.addWidget(QLabel("Active Orders:"))
        self.active_orders_table = QTableWidget()
        self.active_orders_table.setColumnCount(6)
        self.active_orders_table.setHorizontalHeaderLabels(["Order ID", "Side", "Type", "Price", "Size", "Status"])
        active_orders_layout.addWidget(self.active_orders_table)
        tables_layout.addLayout(active_orders_layout)
        
        # Order history table
        order_history_layout = QVBoxLayout()
        order_history_layout.addWidget(QLabel("Order History:"))
        self.order_history_table = QTableWidget()
        self.order_history_table.setColumnCount(7)
        self.order_history_table.setHorizontalHeaderLabels(["Order ID", "Side", "Type", "Price", "Size", "Status", "Time"])
        order_history_layout.addWidget(self.order_history_table)
        tables_layout.addLayout(order_history_layout)
        
        layout.addLayout(tables_layout)

        # Initial UI state
        self.on_mode_changed(self.mode_combo.currentText())

    def on_mode_changed(self, mode):
        """Handle UI changes when trading mode is changed"""
        is_grid_mode = mode == "Grid Trading"
        
        # Show/hide grid-specific controls
        self.profit_input.setVisible(is_grid_mode)
        self.profit_layout.itemAt(0).widget().setVisible(is_grid_mode)
        
        # Show/hide volume-specific controls
        self.min_delay_input.setVisible(not is_grid_mode)
        self.max_delay_input.setVisible(not is_grid_mode)
        self.delay_layout.itemAt(0).widget().setVisible(not is_grid_mode)
        self.current_delay_label.setVisible(not is_grid_mode)
        self.current_delay_layout.itemAt(0).widget().setVisible(not is_grid_mode)
        self.trailing_checkbox.setVisible(not is_grid_mode)

    def load_trading_pairs(self):
        self.logger.info("Loading trading pairs...")
        pairs = get_trading_pairs()
        for pair in pairs:
            if pair['quoteSymbol'] == 'USDT':
                self.pair_combo.addItem(pair['symbol'])

    def update_balances(self):
        try:
            balances = get_balances()
            self.balance_table.setRowCount(len(balances))
            for i, balance in enumerate(balances):
                self.balance_table.setItem(i, 0, QTableWidgetItem(balance['symbol']))
                self.balance_table.setItem(i, 1, QTableWidgetItem(str(balance['balance'])))
                self.balance_table.setItem(i, 2, QTableWidgetItem(str(balance['free'])))
        except Exception as e:
            self.logger.error(f"Error updating balances: {e}")

    def update_orders(self):
        try:
            current_symbol = self.pair_combo.currentText()
            
            # Update active orders
            active_orders = get_active_orders(current_symbol)
            self.active_orders_table.setRowCount(len(active_orders))
            for i, order in enumerate(active_orders):
                self.active_orders_table.setItem(i, 0, QTableWidgetItem(str(order['orderId'])))
                self.active_orders_table.setItem(i, 1, QTableWidgetItem(order['side']))
                self.active_orders_table.setItem(i, 2, QTableWidgetItem(order['type']))
                self.active_orders_table.setItem(i, 3, QTableWidgetItem(str(order['price'])))
                self.active_orders_table.setItem(i, 4, QTableWidgetItem(str(order['size'])))
                self.active_orders_table.setItem(i, 5, QTableWidgetItem(order['status']))
            
            # Update order history
            order_history = get_order_history(current_symbol)
            self.order_history_table.setRowCount(len(order_history))
            for i, order in enumerate(order_history):
                self.order_history_table.setItem(i, 0, QTableWidgetItem(str(order['orderId'])))
                self.order_history_table.setItem(i, 1, QTableWidgetItem(order['side']))
                self.order_history_table.setItem(i, 2, QTableWidgetItem(order['type']))
                self.order_history_table.setItem(i, 3, QTableWidgetItem(str(order['price'])))
                self.order_history_table.setItem(i, 4, QTableWidgetItem(str(order['size'])))
                self.order_history_table.setItem(i, 5, QTableWidgetItem(order['status']))
                self.order_history_table.setItem(i, 6, QTableWidgetItem(
                    time.strftime('%Y-%m-%d %H:%M:%S', 
                                time.localtime(order['time'] / 1_000_000))
                ))
        except Exception as e:
            self.logger.error(f"Error updating orders: {e}")

    def start_bot(self):
        try:
            params = {
                'symbol': self.pair_combo.currentText(),
                'usdt_amount': float(self.usdt_input.text()),
                'num_orders': int(self.orders_input.text()),
                'price_drop': float(self.drop_input.text()),
                'first_order_offset': float(self.offset_input.text()),
                'mode': self.mode_combo.currentText(),
                'price_deviation_pct': float(self.deviation_input.text())
            }

            # Add mode-specific parameters
            if params['mode'] == "Grid Trading":
                params.update({
                    'target_profit_pct': float(self.profit_input.text())
                })
            else:  # Volume Trading
                params.update({
                    'min_delay': float(self.min_delay_input.text()),
                    'max_delay': float(self.max_delay_input.text()),
                    'use_trailing_limit': self.trailing_checkbox.isChecked()
                })
            
            self.bot_thread = BotWorker(params)
            self.bot_thread.delay_updated.connect(self.update_current_delay)
            self.bot_thread.start()
            
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.mode_combo.setEnabled(False)
            self.status_label.setText("Bot Status: Running")
            
        except ValueError as e:
            self.logger.error(f"Invalid input parameters: {e}")
        except Exception as e:
            self.logger.error(f"Error starting bot: {e}")

    def stop_bot(self):
        if self.bot_thread and self.bot_thread.isRunning():
            self.bot_thread.stop()
            self.bot_thread.wait()
            
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.mode_combo.setEnabled(True)
        self.status_label.setText("Bot Status: Stopped")
        self.current_delay_label.setText("Not active")

    def update_current_delay(self, delay):
        """Update the display of current delay before market sell"""
        self.current_delay_label.setText(f"{delay:.1f} seconds")
import sys
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow
from utils.logger import setup_logger

def main():
    logger = setup_logger()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
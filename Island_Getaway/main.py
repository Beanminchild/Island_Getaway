# python
# Dynamic Island-like effect for MacBook Pro notch area
# Requires: pip install PyQt5

import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QSizePolicy, QPushButton, QHBoxLayout
from IslandGetaway import DynamicIsland

if __name__ == "__main__":
    app = QApplication(sys.argv)
    island = DynamicIsland()
    sys.exit(app.exec_())

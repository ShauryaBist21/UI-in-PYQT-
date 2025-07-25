import sys
import cv2
import os
import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QSlider, QFileDialog
)
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor
from PyQt5.QtCore import QTimer, Qt

from ui_component import VIPERS_UI
from PyQt5.QtWidgets import QApplication
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VIPERS_UI()
    window.show()
    sys.exit(app.exec_())

import sys
from PyQt5.QtWidgets import QApplication
from ui_component import VIPERS_UI

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VIPERS_UI()
    window.show()
    sys.exit(app.exec_())

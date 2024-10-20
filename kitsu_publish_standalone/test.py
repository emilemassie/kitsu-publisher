import sys

from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtWidgets import QApplication


# QSvgWidget is good to use when you want to make SVG-related widget.
class AnimatedSvgExample(QSvgWidget):
    def __init__(self):
        super().__init__()
        self.__initUi()

    def __initUi(self):
        r = self.renderer()
        # set FPS of SVG animation.
        r.setFramesPerSecond(60) 
        ico_filename = 'icons/loading.svg'
        # set SVG icon to QSvgWidget.
        r.load(ico_filename) 


if __name__ == "__main__":
    app = QApplication(sys.argv)
    r = AnimatedSvgExample()
    r.show()
    sys.exit(app.exec_())

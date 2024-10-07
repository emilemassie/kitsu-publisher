import os, sys

from PySide2.QtWidgets import QApplication, QDialog
from PySide2.QtUiTools import QUiLoader
from PySide2.QtCore import Qt
from PySide2 import QtCore


class progress_dialog(QDialog):
        def __init__(self, parent=None):
            QDialog.__init__(self, parent)
            self.setWindowFlags(Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint)
            self.setWindowTitle("Kitsu Connect - Progress")

            
            # Load the UI file directly
            ui_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", 'progress_dialog.ui')
            loader = QUiLoader()
            self.ui = loader.load(ui_file, self)
            self.setFixedSize(400, 92)
            
        
        def update(self, int_value):
            self.ui.progressBar.setValue(int_value)
            QtCore.QCoreApplication.processEvents()
            
        def setText(self, text):
            self.ui.label.setText(text)

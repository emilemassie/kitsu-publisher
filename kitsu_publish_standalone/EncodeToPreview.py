import sys
import subprocess
import os
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtCore import Qt

class FFmpegWorker(QtCore.QThread):
    progress = QtCore.pyqtSignal(int)
    finished = QtCore.pyqtSignal()
    log_update = QtCore.pyqtSignal(str)  # Signal to update the log

    def __init__(self, input_files, output_file, fps):
        super().__init__()
        self.input_files = input_files
        self.output_file = output_file
        self.fps = fps

    def run(self):
        try:
            if len(self.input_files) == 1:
                # Single file conversion
                self.log_update.emit("Retrieving file...")
                cmd = ["ffmpeg", "-y", "-i", self.input_files[0], "-c:v", "libx264", "-crf", "23", "-preset", "medium", "-c:a", "aac", "-b:a", "128k", self.output_file]
                self.log_update.emit("Converting...")
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            else:
                # Image sequence conversion
                self.log_update.emit("Retrieving image sequence files...")
                with open("temp_file_list.txt", "w") as f:
                    for file in self.input_files:
                        f.write(f"file '{file}'\n")
                cmd = [
                    "ffmpeg",
                    "-y",  # Allow overwriting
                    "-f", "concat",
                    "-safe", "0",
                    "-r", str(self.fps),
                    "-i", "temp_file_list.txt",
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-r", str(self.fps),
                    self.output_file
                ]
                self.log_update.emit("Converting...")
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

            # Process the output for progress
            for line in process.stderr:
                if "frame=" in line:
                    # Extract the frame number from the output
                    frame_data = line.split("frame=")[1].split()[0]
                    if frame_data.isdigit():
                        self.progress.emit(int(frame_data))  # Emit progress signal with frame count

            process.wait()  # Wait for the process to complete
        finally:
            if os.path.exists("temp_file_list.txt"):
                os.remove("temp_file_list.txt")
            self.finished.emit()  # Emit finished signal when done


class DropZoneLabel(QtWidgets.QLabel):
    fileSelected = QtCore.pyqtSignal(list)  # Signal to emit selected files

    def __init__(self, title):
        super().__init__(title)
        self.setAcceptDrops(True)
        self.setStyleSheet("border: 1.5px dashed #888; padding: 80px 20px;")
        self.setAlignment(QtCore.Qt.AlignCenter)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        self.fileSelected.emit(files)  # Emit the selected files

    def mouseDoubleClickEvent(self, event):
        self.open_file_dialog()

    def open_file_dialog(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Select Files", "", "All Files (*)")
        if files:
            self.fileSelected.emit(files)  # Emit the selected files


class FFmpegGUI(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Quick Preview Maker")
          # Increased window size

        layout = QtWidgets.QVBoxLayout()
        box_h =  QtWidgets.QHBoxLayout()
        box_v = QtWidgets.QVBoxLayout()

        # Drop zone for single file
        self.single_file_label = DropZoneLabel("Drag & Drop Single Media File Here")
        self.single_file_label.fileSelected.connect(self.set_single_file)
        self.single_file_label.setSizePolicy(1,1)
        box_h.addWidget(self.single_file_label)

    

        
        # Drop zone for image sequence
        self.sequence_label = DropZoneLabel("Drag & Drop Image Sequence Here")
        self.sequence_label.fileSelected.connect(self.set_image_sequence)
        box_h.addWidget(self.sequence_label)

        lay = QtWidgets.QHBoxLayout()

        spacer = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        lay.addItem(spacer)
        self.fps_label = QtWidgets.QLabel("FPS:")
        self.fps_label.setSizePolicy(0,0)
        lay.addWidget(self.fps_label)

        self.fps_entry = QtWidgets.QLineEdit("24")
        self.fps_entry.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.fps_entry.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed))
        double_validator = QDoubleValidator(self.fps_entry)
        double_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.fps_entry.setValidator(double_validator)
        lay.addWidget(self.fps_entry)

        box_v.addLayout(box_h)
        box_v.addLayout(lay)
        layout.addLayout(box_v)


        # Add a separator
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)  # Use QFrame.Shape.VLine for a vertical separator
        separator.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        layout.addWidget(separator)


        # Output field and button
        output_layout = QtWidgets.QHBoxLayout()
        self.output_field = QtWidgets.QLineEdit()
        self.output_field.setPlaceholderText("Select Output MP4")
        self.output_field.setReadOnly(True)  # Make the field read-only
        output_layout.addWidget(self.output_field)

        # Set default output path to user's Documents folder
        documents_path = os.path.expanduser("~/Documents/")
        self.output_btn = QtWidgets.QPushButton("Browse")
        self.output_btn.clicked.connect(lambda: self.select_output_file(documents_path))
        output_layout.addWidget(self.output_btn)

        layout.addLayout(output_layout)

        self.convert_btn = QtWidgets.QPushButton("Convert")
        self.convert_btn.clicked.connect(self.convert)
        layout.addWidget(self.convert_btn)

        # Progress bar
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Log view
        self.log_view = QtWidgets.QTextEdit()
        self.log_view.setReadOnly(True)  # Make the log view read-only
        self.log_view.setMaximumHeight(120)  # Limit height of log view
        layout.addWidget(self.log_view)

        # Spacer to push log view to the bottom
        #spacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        #layout.addItem(spacer)

        self.setLayout(layout)

        self.input_files = []
        self.output_file = ""

    def update_log(self, message):
        self.log_view.append(message)  # Append message to log view

    def set_single_file(self, files):
        if files:
            self.input_files = [files[0]]  # Take the first file for single file conversion
            self.single_file_label.setText(f"Single File: {self.input_files[0]}")

    def set_image_sequence(self, files):
        if files:
            self.input_files = sorted(files)  # Sort files to ensure correct order
            self.sequence_label.setText(f"Selected {len(files)} Files")

    def select_output_file(self, default_path):
        file, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Select Output MP4", default_path, "MP4 files (*.mp4)")
        if file:
            self.output_file = file
            self.output_field.setText(file)  # Update the text field with the selected output file
            self.update_log(f"Output: {file}")

    def convert(self):
        if not self.input_files or not self.output_file:
            QtWidgets.QMessageBox.critical(self, "Error", "Please select input and output files")
            return

        try:
            fps = float(self.fps_entry.text())
            if fps <= 0:
                raise ValueError("FPS must be a positive number")
        except ValueError as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Invalid FPS value: {e}")
            return

        self.progress_bar.setValue(0)  # Reset progress bar
        self.progress_bar.setMaximum(100)  # Set maximum for progress bar

        self.convert_btn.setEnabled(False)  # Disable the Convert button
        self.worker = FFmpegWorker(self.input_files, self.output_file, fps)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.log_update.connect(self.update_log)  # Connect log update signal
        self.worker.start()  # Start the thread

    def update_progress(self, frame):
        # Update the progress bar based on the number of frames processed
        self.progress_bar.setValue(frame)
        self.update_log('Exporting frame: ' + str(frame))

    def on_finished(self):
        QtWidgets.QMessageBox.information(self, "Success", "Conversion completed successfully!")
        self.progress_bar.setValue(100)  # Set progress bar to complete
        self.convert_btn.setEnabled(True)  # Re-enable the Convert button


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = FFmpegGUI()
    window.show()
    sys.exit(app.exec_())

import sys
import subprocess
import os
import tempfile
import json

from PyQt5 import QtWidgets, QtCore, QtGui, uic
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtCore import Qt, QPoint
import gazu

parent_folder = os.path.dirname(__file__)


# Determine the ffmpeg directory based on the OS
if sys.platform == "win32":  # Windows
    ffmpeg_dir = os.path.join(os.path.dirname(__file__), 'ffmpeg_win', 'bin', 'ffmpeg.exe')
elif sys.platform == "darwin":  # macOS
    ffmpeg_dir = os.path.join(os.path.dirname(__file__), 'ffmpeg_osx', 'bin', 'ffmpeg')
elif sys.platform.startswith("linux"):  # Linux
    ffmpeg_dir = os.path.join(os.path.dirname(__file__), 'ffmpeg_linux', 'bin', 'ffmpeg')
else:
    raise EnvironmentError("Unsupported operating system")



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
            # Set the creation flags to avoid a popup window on Windows
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

            if len(self.input_files) == 1:
                # Single file conversion
                self.log_update.emit("Retrieving file...")
                cmd = [
                    ffmpeg_dir,
                    "-y", "-i", self.input_files[0], "-c:v", "libx264",
                    "-crf", "23", "-preset", "medium", "-c:a", "aac", "-b:a", "128k", self.output_file
                ]
                
            else:
                # Image sequence conversion
                self.log_update.emit("Retrieving image sequence files...")
                with open("temp_file_list.txt", "w") as f:
                    for file in self.input_files:
                        f.write(f"file '{file}'\n")
                
                cmd = [
                    ffmpeg_dir,
                    "-y", "-f", "concat", "-safe", "0", "-r", str(self.fps),
                    "-i", "temp_file_list.txt", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(self.fps),
                    "-loglevel", "info", self.output_file
                ]

            # Use subprocess.Popen to capture output in real-time and avoid window popup
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
                creationflags=creationflags
            )

            # Monitor the output for progress updates
            while True:
                line = process.stderr.readline()  # Read the stderr line by line
                if line == '' and process.poll() is not None:
                    break  # Exit if no more output and the process has finished

                if "frame=" in line:
                    # Extract frame information and emit progress signal
                    frame_data = line.split("frame=")[1].split()[0]
                    if frame_data.isdigit():
                        self.progress.emit(int(frame_data))  # Emit progress signal with frame count

                # Optionally, emit other updates based on different ffmpeg output logs
                #if line:
                #    self.log_update.emit(line.strip())  # Emit log updates for other messages

            process.wait()  # Ensure the process completes before moving on
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

class kitsu_settings(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__()

        uic.loadUi(os.path.join(parent_folder,'ui','kitsu_publisher_settings.ui'), self) 

        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowMinimizeButtonHint)
        self.setWindowIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__),'icons','icon.png')))

        self.parent = parent

        # Remove the window frame and make the window transparent
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        #self.setAttribute(Qt.WA_TranslucentBackground)

        # Variables to track mouse position for dragging
        self.old_position = QtCore.QPoint()
        self.exit_button.released.connect(self.close)
        self.save_button.released.connect(self.save_pressed)

        self.access_token = None
        self.settings_dict = {}

        self.settings_file = os.path.join(os.path.dirname(__file__),os.getlogin()+'_settings.conf')

        print('Loading Settings : ')
        if self.load_settings():
            print('user config loaded')
            if self.check_connection():
                print('connected')
            
        

    def check_connection(self):
        
        if self.access_token:
            token = {'access_token': self.access_token}
            gazu.client.set_host(self.url+'/api')
            gazu.client.set_tokens(token)
            user = gazu.client.get_current_user()
            return True
        else:
            print('No acces token')
            return False

    def get_kitsu_token(self):
        try:
            self.user = self.t_user.text()
            self.url = self.t_url.text()
            gazu.client.set_host(self.url+'/api')
            gazu.log_in(self.user, self.t_pwd.text())
            self.access_token = gazu.refresh_token()['access_token']
            print ('Got token : '+ self.access_token)
            return self.access_token
        except Exception as eee:
            print('Cannot Authenticate : \n')
            print(str(eee))
            self.setConnectStatus(False)
            self.status_c.setText('<span style="color:red;">ERROR CONNECTING</span>'+str(eee))
            self.parent.update_log('<span style="color:red;">ERROR CONNECTING</span>'+str(eee))

            return False

    def save_pressed(self):
        if self.get_kitsu_token():
            self.save_settings()
            self.load_settings()
            self.close()
            return True
        else:

            return False
    
    def setConnectStatus(self,is_good):
        if is_good:
            self.parent.t_url.setText(self.url)
            self.parent.t_user.setText(self.user)
            self.parent.t_status.setText('<span style="color:green;">CONNECTED')
            self.status_c.setText('<span style="color:green;">CONNECTED')
            self.parent.build_tasks_tree()
            self.parent.connect_status = True
            return True
        else:
            self.parent.t_url.setText('https://kitsu.exemple.com')
            self.parent.t_user.setText('user@exemple.com')
            self.parent.t_status.setText('<span style="color:red;">NOT CONNECTED')
            self.status_c.setText('<span style="color:NOT CONNECTED;">')
            self.parent.connect_status = False
            return False

    def load_settings(self):
        try:
            with open(self.settings_file, 'r') as f:
                self.settings_dict = json.load(f)
                self.url = self.settings_dict['host']
                self.user = self.settings_dict['username']
                self.access_token = self.settings_dict['key']

                self.t_url.setText(self.url)
                self.t_user.setText(self.user)

                if self.check_connection():
                    self.setConnectStatus(True)
                    return True
                else:
                    self.setConnectStatus(False)
                    return False
        except Exception as eee:
            self.setConnectStatus(False)
            print('Cannot load settings')
            print(eee)
            return False

    def save_settings(self):
        new_dict = {
            "host": self.url,
            "username":self.user,
            "key": self.access_token
        }
        j = json.dumps(new_dict, indent=4)
        with open(self.settings_file, 'w') as f:
            print(j, file=f)

        self.parent.update_log('Saved Settings')

    def mousePressEvent(self, event):




        if event.button() == Qt.LeftButton:
            self.old_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.old_position)
            event.accept()


class kitsu_publisher_standalone_gui(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()


        QtCore.QDir.addSearchPath('icons', os.path.join(os.path.dirname(__file__), 'icons'))
        uic.loadUi(os.path.join(parent_folder,'ui','kitsu_publisher_standalone.ui'), self) 

        


        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowMinimizeButtonHint)
        self.setWindowIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__),'icons','icon.png')))


        # Remove the window frame and make the window transparent
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        #self.setAttribute(Qt.WA_TranslucentBackground)

        # Variables to track mouse position for dragging

        self._isResizing = False
        self._isDragging = False
        self._dragPosition = QPoint()
        self._resizeMargin = 10  # Margin around edges for resizing
        self._dragArea = None

        self.exit_button.released.connect(self.close)
        self.settings_button.released.connect(self.show_settings)
        self.connect_status = None
        self.ks = kitsu_settings(self)


        self.input_files = None
        self.context = None
        #self.t_task_stat.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)


        self.tree_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        self.show_only_my_tasks.stateChanged.connect(self.build_tasks_tree)

        self.file_manager = DropZoneLabel('test')
        self.file_manager.setText(self.file_drop.text())  # Keep the existing text
        self.file_manager.setGeometry(self.file_drop.geometry())
        self.file_manager.fileSelected.connect(self.set_files)

        self.ff_layout.replaceWidget(self.file_drop, self.file_manager)
        self.file_drop.deleteLater()
        self.publish_button.released.connect(self.launch_publisher)
        #self.file_drop.mouseDoubleClickEvent.connect(self.file_browse)

        if self.ks.check_connection():
            self.update_log('User Config Settings Loaded !!!')
            self.build_tasks_tree()



    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Detect if we're clicking in a resize area
            self._dragArea = self._detectDragArea(event.pos())
            if self._dragArea:
                self._isResizing = True
                self._dragPosition = event.globalPos()
                event.accept()
            else:
                # Otherwise, assume we're dragging the window
                self._isDragging = True
                self.old_position = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._isResizing and self._dragArea:
            # Calculate how much the mouse has moved
            delta = event.globalPos() - self._dragPosition
            self._resizeWindow(delta)
            self._dragPosition = event.globalPos()
            event.accept()
        elif self._isDragging:
            # Move the window if it's being dragged
            self.move(event.globalPos() - self.old_position)
            event.accept()
        else:
            # Change cursor shape when hovering over edges or corners
            self._setCursorShape(event.pos())
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Stop dragging and resizing
            self._isResizing = False
            self._isDragging = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _detectDragArea(self, pos):
        """ Detect which area of the window is being clicked for resizing. """
        rect = self.rect()
        top, left, right, bottom = rect.top(), rect.left(), rect.right(), rect.bottom()
        margin = self._resizeMargin

        if left <= pos.x() <= left + margin and top <= pos.y() <= top + margin:
            return 'top-left'
        elif right - margin <= pos.x() <= right and top <= pos.y() <= top + margin:
            return 'top-right'
        elif left <= pos.x() <= left + margin and bottom - margin <= pos.y() <= bottom:
            return 'bottom-left'
        elif right - margin <= pos.x() <= right and bottom - margin <= pos.y() <= bottom:
            return 'bottom-right'
        elif left <= pos.x() <= left + margin:
            return 'left'
        elif right - margin <= pos.x() <= right:
            return 'right'
        elif top <= pos.y() <= top + margin:
            return 'top'
        elif bottom - margin <= pos.y() <= bottom:
            return 'bottom'
        return None

    def _resizeWindow(self, delta):
        """ Resize the window based on the mouse movement delta. """
        if self._dragArea == 'right':
            self.setGeometry(self.x(), self.y(), self.width() + delta.x(), self.height())
        elif self._dragArea == 'bottom':
            self.setGeometry(self.x(), self.y(), self.width(), self.height() + delta.y())
        elif self._dragArea == 'bottom-right':
            self.setGeometry(self.x(), self.y(), self.width() + delta.x(), self.height() + delta.y())
        elif self._dragArea == 'left':
            self.setGeometry(self.x() + delta.x(), self.y(), self.width() - delta.x(), self.height())
        elif self._dragArea == 'top':
            self.setGeometry(self.x(), self.y() + delta.y(), self.width(), self.height() - delta.y())
        elif self._dragArea == 'top-left':
            self.setGeometry(self.x() + delta.x(), self.y() + delta.y(), self.width() - delta.x(), self.height() - delta.y())
        elif self._dragArea == 'top-right':
            self.setGeometry(self.x(), self.y() + delta.y(), self.width() + delta.x(), self.height() - delta.y())
        elif self._dragArea == 'bottom-left':
            self.setGeometry(self.x() + delta.x(), self.y(), self.width() - delta.x(), self.height() + delta.y())

    def _setCursorShape(self, pos):
        """ Change the cursor shape based on the drag area detected. """
        area = self._detectDragArea(pos)
        if area in ['top-left', 'bottom-right']:
            self.setCursor(Qt.SizeFDiagCursor)
        elif area in ['top-right', 'bottom-left']:
            self.setCursor(Qt.SizeBDiagCursor)
        elif area in ['left', 'right']:
            self.setCursor(Qt.SizeHorCursor)
        elif area in ['top', 'bottom']:
            self.setCursor(Qt.SizeVerCursor)
        else:
            self.setCursor(Qt.ArrowCursor)




    def set_files(self, files):
        self.input_files = sorted(files)
        self.update_log('Selected '+str(len(files))+' files')
        if len(files)>1:
            self.file_manager.setText(f'{str(len(files))} files\n\n{os.path.basename(files[0])}\n[...]\n{os.path.basename(files[-1])}')
        else:
            self.file_manager.setText(f'{os.path.basename(files[0])}')
        self.check_button_enable()
        

    def find_or_create_child(self, parent_item, child_name):
        """ Helper function to find a child with the given name or create a new one """
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            if child.text(0) == child_name:
                return child

        # If the child does not exist, create and add it
        new_child = QtWidgets.QTreeWidgetItem([child_name])
        parent_item.addChild(new_child)
        return new_child

    def on_item_double_clicked(self, item, column):
        # Print the stored context_id if it's a leaf item (Task level)
        context_id = item.data(1, 0)
        if context_id:
            self.set_context(context_id)
        else:
            self.set_context()

    def check_button_enable(self):
        if self.context and self.input_files:
            self.publish_button.setEnabled(True)
        else:
            self.publish_button.setEnabled(False)

    def set_context(self, context_id=None):
        if context_id:
            self.update_log(f"Setting Context ID: {context_id}")
            self.t_context.setText(context_id)
            self.context = context_id
        else:
            self.t_context.setText('')
            self.context = None
        self.check_button_enable()

        
    def build_tasks_tree(self):
        self.tree_widget.clear()
        self.t_task_stat.clear()

        for stat in reversed(gazu.task.all_task_statuses()):
            self.t_task_stat.addItem(stat['name'])


        if self.connect_status:
            self.update_log('Building Tree View...')

            if self.show_only_my_tasks.isChecked():
                tasks = gazu.user.all_tasks_to_do()
            else:
                projects = gazu.project.all_open_projects()  # Retrieves all open projects
                # Step 3: Get all tasks for each project
                tasks = []  # Initialize a list to store all tasks

                for project in projects:
                    # Retrieve tasks for the current project
                    g_tasks = gazu.task.all_tasks_for_project(project)
                    tasks.extend(g_tasks)  # Add tasks to the all_tasks list

            self.update_log('Found '+str(len(tasks))+' tasks')

            data = []
            for task in tasks:
                task = gazu.task.get_task(task)
                try:
                    seq = task['sequence']['name']
                except:
                    seq = task['entity_type']['name']
                
                if seq is None:
                    seq = task['entity_type_name']
                dd = {
                    'project': task['project']['name'],
                    'type': task['task_type']['for_entity'],
                    'seq': seq,
                    'element': task['entity']['name'],
                    'task': task['task_type']['name'],
                    'context_id': task['id']
                }
                data.append(dd)

            root_items = {}
            for item_data in data:
                # Create hierarchy: Project > Type > Sequence > Element > Task
                project_name = item_data.get('project', 'Unknown Project')  # Add a project key
                type_name = item_data['type']
                seq_name = item_data['seq']
                element_name = item_data['element']
                task_name = item_data['task']
                context_id = item_data['context_id']

                # Create or get the Project level item
                if project_name not in root_items:
                    project_item = QtWidgets.QTreeWidgetItem([project_name])
                    self.tree_widget.addTopLevelItem(project_item)
                    root_items[project_name] = {}
                
                project_item = self.tree_widget.findItems(project_name, Qt.MatchExactly | Qt.MatchRecursive)[0]

                # Create or get the Type level item
                if type_name not in root_items[project_name]:
                    type_item = QtWidgets.QTreeWidgetItem([type_name])
                    project_item.addChild(type_item)
                    root_items[project_name][type_name] = type_item
                else:
                    type_item = root_items[project_name][type_name]

                # Create or get the Sequence level item
                seq_item = self.find_or_create_child(type_item, seq_name)

                # Create or get the Element level item
                element_item = self.find_or_create_child(seq_item, element_name)

                # Create the Task level item
                task_item = QtWidgets.QTreeWidgetItem([task_name])
                # Store the context_id in the task item for easy retrieval
                task_item.setData(1, 0, context_id)

                # Add Task item under the Element level
                element_item.addChild(task_item)


    def show_settings(self):
        self.update_log('Open Connection Settings')
        self.ks.show()




        #self.init_ui()

    def init_ui(self):
        
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
        #separator = QtWidgets.QFrame()
        #separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)  # Use QFrame.Shape.VLine for a vertical separator
        #separator.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        #layout.addWidget(separator)

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
        self.log_view.moveCursor(QtGui.QTextCursor.End)


    def launch_publisher(self):
        self.convert()

    def publish_file_to_kitsu(self):

        try:
            status = gazu.task.get_task_status_by_name(self.t_task_stat.currentText())
            task = gazu.task.get_task(self.context)
            file_string = '\n\n<hr><b><u>FILE :</b></u><i>\n' + str(self.output_file) + '</i>\n'
            comment = gazu.task.add_comment(task, status, self.t_comment.toPlainText()+file_string)

            preview_file = gazu.task.add_preview(
                    task,
                    comment,
                    self.output_file
                )

            # Remove the temporary playblast file
            if os.path.exists(self.output_file):
                os.remove(self.output_file)
            return True
        except Exception as eee:
            self.update_log(f'<span style="color:red;">Cannot Publish File:\n\n</span>{str(eee)}')
            return False
        self.progress_bar.setValue(80)



    def convert(self):
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        self.output_file = temp_file.name
        print(self.output_file)

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

        self.publish_button.setEnabled(False)  # Disable the Convert button
        self.worker = FFmpegWorker(self.input_files, self.output_file, fps)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.log_update.connect(self.update_log)  # Connect log update signal
        self.worker.start()  # Start the thread

    def update_progress(self, frame):
        # Update the progress bar based on the number of frames processed
        self.progress_bar.setValue(frame)
        if frame > 0 :
            self.update_log('Exporting frame: ' + str(frame))

    def on_finished(self):
        self.update_log(f'Uploaded Preview File !!!')
        #QtWidgets.QMessageBox.information(self, "Success", "Conversion completed successfully!")
        self.progress_bar.setValue(100)  # Set progress bar to complete
        self.publish_button.setEnabled(True)  # Re-enable the Convert button
        self.publish_file_to_kitsu()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = kitsu_publisher_standalone_gui()
    window.show()
    sys.exit(app.exec_())

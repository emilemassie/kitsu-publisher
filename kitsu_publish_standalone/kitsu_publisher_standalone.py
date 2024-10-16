import sys
import subprocess
import os, getpass
import tempfile
import json

import requests
import zipfile
import shutil

from PyQt5 import QtWidgets, QtCore, QtGui, uic
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QMessageBox
import gazu



_VERSION = "1.0.5"
parent_folder = os.path.dirname(__file__)

if getattr(sys, 'frozen', False):
    basedir = sys._MEIPASS
else:
    basedir = os.path.dirname(os.path.abspath(__file__))
    basedir = str(basedir)

ffmpeg_exec = basedir+'/ffmpeg.exe'

# Determine the ffmpeg directory based on the OS
# if sys.platform == "win32":  # Windows
#     ffmpeg_dir = os.path.join(os.path.dirname(__file__), 'ffmpeg_win', 'bin', 'ffmpeg.exe')
# elif sys.platform == "darwin":  # macOS
#     ffmpeg_dir = os.path.join(os.path.dirname(__file__), 'ffmpeg_osx', 'bin', 'ffmpeg')
# elif sys.platform.startswith("linux"):  # Linux
#     ffmpeg_dir = os.path.join(os.path.dirname(__file__), 'ffmpeg_linux', 'bin', 'ffmpeg')
# else:
#     raise EnvironmentError("Unsupported operating system")
ffmpeg_dir = ffmpeg_exec

from appdirs import user_config_dir

# Get the current username
username = getpass.getuser()

# Define your application name and author/company name
app_name = "kitsu-publisher"
app_author = "kitsu-publisher-standalone"  # Optional, not needed for Linux

# Get the user-specific configuration directory
config_dir = user_config_dir(app_name, app_author)

# Create the configuration directory if it doesn't exist
os.makedirs(config_dir, exist_ok=True)

# Define the path for your configuration file
config_file = os.path.join(config_dir, f"{username}_settings.conf")

print(f"Configuration file path: {config_file}")

from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot



class Updater(QThread):
    update_progress = pyqtSignal(str)
    update_finished = pyqtSignal(bool, str)

    def __init__(self, github_repo, updatefile):
        QThread.__init__(self)
        self.github_repo = github_repo
        self.zip_ref = None
        self.updatefile = updatefile

    def run(self):
        try:
            response = requests.get(f"https://api.github.com/repos/{self.github_repo}")
            self.latest_release = response.json()
            
            # Download the update
            self.update_progress.emit("<b>Downloading update...</b>")
            zip_url = self.latest_release['assets'][0]['browser_download_url']
            r = requests.get(zip_url)
            with open(self.updatefile, 'wb') as f:
                f.write(r.content)

            self.update_finished.emit(True, "New Version Downloaded ! Please close and replace the application.")
        except Exception as e:
            raise e
            self.update_finished.emit(False, f"Update failed: {str(e)}")


class Worker(QObject):
    finished = pyqtSignal()  # Signal to indicate when the worker is done
    progress = pyqtSignal(str)  # Signal to send progress back to the main thread

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func  # Store the reference to the function to be executed
        self.args = args  # Store any positional arguments for the function
        self.kwargs = kwargs  # Store any keyword arguments for the function

    @pyqtSlot()
    def run(self):
        # Execute the function with any given arguments
        self.func(*self.args, **self.kwargs)
        self.finished.emit()  # Emit the finished signal when done


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
        print(self.input_files)
        try:
            # Set the creation flags to avoid a popup window on Windows
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

            if len(self.input_files) == 1:
                # Single file conversion
                self.log_update.emit("Retrieving file...")
                cmd = [
                    ffmpeg_exec,
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
                    "-apply_trc","bt709",
                    "-y", "-f", "concat", "-safe", "0", "-r", str(self.fps),
                    "-i", "temp_file_list.txt",
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-r", str(self.fps),  # Linear to BT.709 with gamma correction
                    "-loglevel", "info",
                    self.output_file
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

    def __init__(self, title, parent):
        super().__init__(title)
        self.parent = parent
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
        for i in files:
            if os.path.isdir(i):
                self.parent.update_log(f"{i} is a directory, adding all files in directory")
                files.remove(i)
                for g in os.listdir(i):
                    files.append(os.path.join(i,g))

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

        self.settings_file = config_file

        self.parent.update_log(f"Checking for settings in : {config_file}")
        if self.load_settings():
            self.parent.update_log('User configuration loaded !')
            self.check_connection()
                
    def check_connection(self):
        if self.access_token:
            token = {'access_token': self.access_token}
            gazu.client.set_host(self.url+'/api')
            gazu.client.set_tokens(token)
            user = gazu.client.get_current_user()
            self.parent.connection_status = True
            return True
        else:
            self.parent.connection_status = True
            return False

    def get_kitsu_token(self):
        try:
            self.user = self.t_user.text()
            self.url = self.t_url.text()
            gazu.client.set_host(self.url+'/api')
            gazu.log_in(self.user, self.t_pwd.text())
            self.access_token = gazu.refresh_token()['access_token']
            return self.access_token
        except Exception as eee:
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

        # updates
        self.current_version = _VERSION  # Set your current version here
        self.github_repo = "emilemassie/kitsu-publisher/releases/tags/standalone"  # Set your GitHub repo here
        self.check_for_updates()

        self.thread = QThread()

        # Create a Worker object and pass the print_hello function
        self.worker = Worker(self.refresh_tree)

        # Move the worker to the thread
        self.worker.moveToThread(self.thread)

        # Connect signals and slots
        self.thread.started.connect(self.worker.run)          # Start the worker's run method when the thread starts
        self.worker.finished.connect(self.thread.quit)        # Quit the thread when the worker finishes
        #self.worker.finished.connect(self.worker.deleteLater) # Clean up the worker object
        #self.thread.finished.connect(self.thread.deleteLater) # Clean up the thread object


        self.context = None
        self.ks = kitsu_settings(self)
        self.is_scanning = True


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
        self.connection_status = None

        # Load your image
        self.pixmap = QtGui.QPixmap(os.path.join(os.path.dirname(__file__),'icons', 'loading.svg'))
        self.image_label.setPixmap(self.pixmap)
        self.image_label.setFixedSize(20,20)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.rotate_label)
        self.timer.start(10)  # Rotate every second

        self.angle = 0  # Initial angle


        self.input_files = None
        
        #self.t_task_stat.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)


        self.tree_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        self.show_only_my_tasks.stateChanged.connect(self.build_tasks_tree)

        self.file_manager = DropZoneLabel('test', self)
        self.file_manager.setText(self.file_drop.text())  # Keep the existing text
        self.file_manager.setGeometry(self.file_drop.geometry())
        self.file_manager.fileSelected.connect(self.set_files)

        self.ff_layout.replaceWidget(self.file_drop, self.file_manager)
        self.file_drop.deleteLater()
        self.publish_button.released.connect(self.launch_publisher)
        #self.file_drop.mouseDoubleClickEvent.connect(self.file_browse)

        self.ks.check_connection()


    def check_for_updates(self):
        self.update_log('Checking for updates...')
        try:
            response = requests.get(f"https://api.github.com/repos/{self.github_repo}")
            self.latest_release = response.json()
            latest_version = self.latest_release['name'].split('v')[-1]

            if latest_version > self.current_version:
                reply = QMessageBox.question(self, 'Update Available', 
                                     f"{self.latest_release['name']} is available. Do you want to update?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                if reply == QMessageBox.Yes:
                    self.start_update()
                else:
                    return
            else:
                return
        except Exception as e:
            QMessageBox.warning(self, "Update Check Failed", f"Error: {str(e)}")


    def on_update_progress(self, message):
        self.update_log(message)

    def on_update_finished(self, success, message):
        if success:
            QMessageBox.information(self, "Update Successful", message)
        else:
            QMessageBox.warning(self, "Update Failed", message)
        #self.update_button.setText("Check for Updates")
        
        
    def start_update(self):
        update_file, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Select Update File", self.latest_release['name'], "Zip Files (*.zip)")
        if not update_file:
            return
        self.updater = Updater(self.github_repo, update_file)
        self.updater.update_progress.connect(self.on_update_progress)
        self.updater.update_finished.connect(self.on_update_finished)
        self.updater.start()
        


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


    def rotate_label(self):
            # Increment the angle by 15 degrees
        self.angle += 1  # Rotate by 5 degrees
        if self.angle >= 360:
            self.angle = 0

        # Rotate the pixmap
        transform = QtGui.QTransform().rotate(self.angle)
        rotated_pixmap = self.pixmap.transformed(transform)
        resized_pixmap = rotated_pixmap.scaled(self.image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

        # Update the QLabel with the rotated pixmap
        self.image_label.setPixmap(resized_pixmap)
            

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

        
        if self.thread is not None and self.thread.isRunning():
            self.is_scanning = False

            self.thread.quit()  # Stop the thread's event loop
            self.thread.wait()  # Wait until the thread has finished

        self.is_scanning = True
        self.thread.start()


    def refresh_tree(self):
        self.tree_widget.clear()
        self.t_task_stat.clear()
        self.image_label.setVisible(True)

        self.update_log('')
        self.update_log('Refreshing task list')

        if not self.is_scanning:
            self.update_log('User interupted task loading !', 'red')
            return False

        for stat in reversed(gazu.task.all_task_statuses()):
            self.t_task_stat.addItem(stat['name'])
            self.t_task_stat.setCurrentIndex(0)


        if self.connection_status:
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

            
            self.update_log('Found '+str(len(tasks))+' tasks.\nGathering Kitsu informations...')
            if len(tasks)>40:
                self.update_log("This may take a while...",'orange')

            data = []
            for task in tasks:
                if not self.is_scanning:
                    self.update_log('User interupted task loading !', 'red')
                    self.image_label.setVisible(False)
                    return False
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
            self.update_log('Building Tree View...')
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

            self.update_log('Task Tree Refreshed !', 'green')
            self.update_log('')
            self.image_label.setVisible(False)


    def show_settings(self):
        self.update_log('Open Connection Settings')
        self.ks.show()

    def update_log(self, message, color=None):
        if color:
            self.log_view.append(f'<p style="color:{color};">'+message+'</p> ')
        else:
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

        if not self.input_files or not self.output_file:
            QtWidgets.QMessageBox.critical(self, "Error", "Please select input and output files")
            return

        try:
            fps = float(self.fps_entry.text().replace(',', '.'))
            if fps <= 0:
                QtWidgets.QMessageBox.critical(self, "Error", f"FPS must be a positive number: {e}")
                return
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

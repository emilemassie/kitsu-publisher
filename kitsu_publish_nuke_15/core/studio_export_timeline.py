import gazu
import nuke, hiero
import os, sys, json, shutil, tempfile

from core.settings import KitsuConnectSettings

from PySide2.QtCore import QFile, Qt, QCoreApplication
from PySide2.QtWidgets import QApplication, QMainWindow, QWidget, QFileDialog
from PySide2.QtUiTools import QUiLoader

from core.settings import KitsuConnectSettings
from core.progress_dialog import progress_dialog

folder_path = os.path.dirname(os.path.dirname(__file__))
path = os.path.join(folder_path, "site-packages")
sys.path.append(path)
path = os.path.join(folder_path, "utils")
sys.path.append(path)

class export_timeline(QMainWindow):
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent=None)
        #folder_path = os.path.dirname("C:\\Users\\User\\.nuke\\kitsu-connect\\core")
        self.setWindowTitle("Kitsu Connect - Export Timeline")
        # Load the UI file directly
        ui_file = os.path.join(folder_path, "ui", 'export_timeline.ui')
        loader = QUiLoader()
        self.ui = loader.load(ui_file, self)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint)
        self.settings = KitsuConnectSettings()
        self.prism_folder_path = None 
        self.files_to_copy = None

        if self.settings.connection == True:
            projects = gazu.project.all_open_projects()
            for project in projects:
                self.ui.project_box.addItem(project['name'])
            self.populate_sequences()

        self.ui.project_box.currentTextChanged.connect(self.populate_sequences)
        self.ui.export_button.clicked.connect(self.export_timeline)
        self.ui.prism_box.stateChanged.connect(self.prism_box_changed)
        self.ui.prism_path_button.clicked.connect(self.set_prism_path)

    def set_prism_path(self):
        file_dialog = QFileDialog()
        prism_folder = file_dialog.getExistingDirectory(None, "Select Prism Project Folder", "")
        
        if prism_folder:
            self.ui.prism_path.setText(str(prism_folder))
            self.prism_folder_path = prism_folder

    def prism_box_changed(self):
        enabled_state = self.ui.prism_box.isChecked()
        self.ui.prism_text.setEnabled(enabled_state)
        self.ui.prism_path_button.setEnabled(enabled_state)

    def populate_sequences(self):
        project = gazu.project.get_project_by_name(self.ui.project_box.currentText())
        sequences = gazu.shot.all_sequences_for_project(project['id'])
        self.ui.sequence_box.clear()
        for seq in sequences:
            self.ui.sequence_box.addItem(seq['name'])
            
    def export_timeline(self):

        project = gazu.project.get_project_by_name(self.ui.project_box.currentText())
        seq = gazu.shot.get_sequence_by_name(project, self.ui.sequence_box.currentText())
        
        # Getting selection
        selection = hiero.ui.getTimelineEditor(hiero.ui.activeSequence()).selection()
        self.files_to_copy = []

        if (selection):
            for clip in selection: 
                self.ui.status_text.setText('STATUS : Exporting '+ clip.name())
                shot = gazu.shot.get_shot_by_name(seq,clip.name())

                thumbnail_file = clip.source().thumbnail()

                if shot:
                    question = nuke.ask(shot['name'] + ' Already exists, do you want to update it')
                    #nuke.tprint(shot)
                    if question:
                        shot['data']['frame_in']= clip.sourceIn()+1
                        shot['data']['frame_out']= clip.sourceOut()+1
                        shot['nb_frames'] = clip.sourceOut()-clip.sourceIn()
                        shot['data']['fps'] = clip.source().framerate().toString()
                        gazu.shot.update_shot(shot)

                        # Set the thumbnail for the shot
                        #gazu.shot.update_shot_thumbnail(shot["id"], thumbnail_bytes)
                else:
                    shot = gazu.shot.new_shot(
                        project, 
                        seq, 
                        clip.name(), 
                        frame_in=clip.sourceIn()+1, 
                        frame_out=clip.sourceOut(),
                        nb_frames = clip.sourceOut()-clip.sourceIn(),
                        data = {
                            'fps':clip.source().framerate().toString()
                            }
                    )
                    #gazu.shot.update_shot_thumbnail(shot["id"], thumbnail_bytes)

                if self.ui.prism_box.isChecked():
                    if self.prism_folder_path:
                        #try:
                        project_folder = self.prism_folder_path
                        sequence = seq['name']
                        shot_name = clip.name()
                        frame_in = int(clip.sourceIn()+1)
                        frame_out = int(clip.sourceOut()+1)

                        json_file = os.path.join(project_folder, '00_Pipeline', 'Shotinfo', 'shotInfo.json')
                        shot_folder = os.path.join(project_folder, '03_Production', 'Shots', sequence)

                        # Load the JSON file into a dictionary
                        with open(json_file, 'r') as file:
                            data = json.load(file)

                        # Create shot folder
                        if not os.path.exists(shot_folder):
                            os.makedirs(os.path.join(shot_folder))
                        if not os.path.exists(os.path.join(shot_folder, shot_name)):
                            os.makedirs(os.path.join(shot_folder, shot_name))

                        # set shot name and info
                        try:
                            test_var = data['shots']
                        except:
                            data['shots'] = {}

                        if sequence not in data['shots']:
                            data['shots'][sequence] = {}
                        data['shots'][sequence][shot_name] = {'metadata': {}}

                        # set Shot range
                        if sequence not in data['shotRanges']:
                            data['shotRanges'][sequence] = {}
                        data['shotRanges'][sequence][shot_name] = [frame_in, frame_out]

                        # Save the modified dictionary back to the JSON file
                        with open(json_file, 'w') as file:
                            json.dump(data, file)

                        #set thumbnail
                        thumbnail_path = os.path.join(project_folder, '00_Pipeline', 'Shotinfo', sequence+'-'+shot_name+'_preview.jpg')
                        clip.source().thumbnail().save(thumbnail_path, 'JPEG')
                        #copy the file to prism folders
                        og_file_path = clip.source().mediaSource().firstpath()
                        destination_path = os.path.join(shot_folder, shot_name, 'Renders','external','sourceplate')
                        self.files_to_copy.append([og_file_path, destination_path])
                        
            if self.ui.prism_box.isChecked():
                for file in self.files_to_copy:
                    og_file_path = file[0]
                    destination_path = file[1]
                    try:
                        folder_count = 0
                        for dir in os.listdir(destination_path):
                            if os.path.isdir(os.path.join(destination_path,dir)):
                                folder_count += 1
                    except:
                        pass

                    destination_path_version = os.path.join(destination_path, 'v'+'{:04d}'.format(folder_count+1))
                    complete_dest_path = os.path.join(destination_path_version, 'rgb')

                    if not os.path.exists(complete_dest_path):
                        os.makedirs(complete_dest_path)

                    self.ui.status_text.setText('STATUS : Copying '+ os.path.basename(og_file_path))
                    self.copy_file_with_progress(og_file_path, os.path.join(complete_dest_path, os.path.basename(og_file_path)))

            #except Exception as eee:
            #    nuke.message(str(eee))
            self.ui.status_text.setText('STATUS : Done !!!')
            nuke.message('Exported successfully !!!')
            self.close()

    def scan_for_exr_sequences(self,directory):
        import glob
        from collections import defaultdict
        # Use glob to find all .exr files in the directory
        exr_files = glob.glob(os.path.join(directory, '*.exr'))

        # Dictionary to hold sequences
        sequences = defaultdict(list)

        # Regular expression to match sequence files
        import re
        sequence_pattern = re.compile(r'(.*?)(\d+)(\.exr)$')

        for file in exr_files:
            filename = os.path.basename(file)
            match = sequence_pattern.match(filename)
            if match:
                prefix, frame_number, extension = match.groups()
                sequences[prefix].append((int(frame_number), file))

        # Sort each sequence by frame number
        for prefix in sequences:
            sequences[prefix].sort()

        # Convert each list of tuples to a list of filenames
        for prefix in sequences:
            sequences[prefix] = [file for frame_number, file in sequences[prefix]]

        return sequences

    def copy_file_with_progress(self, source, destination, chunk_size=4096*4096):
        # Get the size of the source file
        #nuke.tprint(source, destination)
        total_size = os.stat(source).st_size
        bytes_written = 0

        if str(source).endswith('.exr'):
            directory = os.path.dirname(source)
            exr_sequences = self.scan_for_exr_sequences(directory)

            # Print the sequences
            for prefix, files in exr_sequences.items():
                print(f"Sequence {prefix}:")
                files_lenght = len(files)
                for file_num, file in enumerate(files):
                    percentage = file_num/files_lenght*100
                    print(percentage)
                    status = f"Copying {os.path.basename(file)}... {percentage:.2f}%"
                    self.ui.status_text.setText(f'STATUS : {status}')
                    QCoreApplication.processEvents()
                    nuke.tprint(status, end='\r')
                    shutil.copyfile(file, os.path.join(os.path.dirname(destination),os.path.basename(file)))

                    

        else:
            with open(source, 'rb') as fsrc, open(destination, 'wb') as fdst:
                while True:
                    # Read a chunk from the source file
                    chunk = fsrc.read(chunk_size)
                    if not chunk:
                        break

                    # Write the chunk to the destination file
                    fdst.write(chunk)
                    bytes_written += len(chunk)

                    # Calculate and print the progress
                    percentage = (bytes_written / total_size) * 100
                    status = f"Copying {os.path.basename(source)}... {percentage:.2f}%"
                    self.ui.status_text.setText(f'STATUS : {status}')
                    QCoreApplication.processEvents()
                    nuke.tprint(status, end='\r')


print('IMPORTING : Kitsu-connect-publisher')

import os, sys
execGui=None
folder_path = os.path.dirname(os.path.dirname(__file__))
path = os.path.join(folder_path, "site-packages")
sys.path.append(path)
path = os.path.join(folder_path, "utils")
sys.path.append(path)

try:
    import gazu
    import json

    import threading

    from PySide2.QtCore import QFile, Qt
    from PySide2.QtWidgets import QApplication, QMainWindow, QWidget, QFormLayout, QFileDialog
    from PySide2.QtUiTools import QUiLoader
    from PySide2.QtGui import QStandardItem, QStandardItemModel, QIcon

    from core.settings import KitsuConnectSettings
    from core.progress_dialog import progress_dialog
    
    class KitsuConnecPublisher(QMainWindow):
        def __init__(self, parent=None):
            QMainWindow.__init__(self, parent)
            self.setWindowFlags(Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
            self.setWindowTitle("Kitsu Connect - Publisher")
            # Load the UI file directly
            ui_file = os.path.join(folder_path, "ui", 'publisher.ui')
            self.settings_json = os.path.join(folder_path,'settings.json')
            loader = QUiLoader()
            self.ui = loader.load(ui_file, self)
            
            self.valid_context = False
            self.ui.publish_button.setEnabled(False)

            self.ui.project_box.currentTextChanged.connect(self.load_tree)
            
            self.ui.showonlymine.stateChanged.connect(self.load_tree)
            self.ui.publish_button.clicked.connect(self.run_publish)
            self.ui.select_publish_file_button.clicked.connect(self.select_file)
            self.ui.treeView.doubleClicked.connect(self.update_context_from_selection)

            self.settings = KitsuConnectSettings()
            self.progress_dialog = progress_dialog()    
            self.context = None

            self.file_path = None
            self.render_function = None

            if self.file_path:
                self.ui.publish_file_path.setText(self.file_path)

            if self.settings.connection == True:
                projects = gazu.project.all_open_projects()
                
                for project in projects:
                    self.ui.project_box.addItem(project['name'])

  
        def send_to_kitsu(self):
            status = gazu.task.get_task_status_by_short_name("wfa")
            task = gazu.task.get_task(self.context)
            comment = gazu.task.add_comment(task, status, self.ui.publish_note.toPlainText())

            self.preview_file = gazu.task.add_preview(
                   task,
                   comment,
                   self.preview_file_path
                )

        def set_file_path(self, file_path):
            self.file_path = file_path
            self.ui.publish_file_path.setText(self.file_path)

        def run_publish(self):
            self.close()
            self.progress_dialog.setText('Initializing ...')
            self.progress_dialog.update(1)
            self.progress_dialog.show()

            self.progress_dialog.setText('Rendering preview file ...')
            self.progress_dialog.update(10)
            
            self.preview_file_path = self.render_function()

            self.progress_dialog.update(50)

            if self.preview_file_path:
                
                thread = threading.Thread(target=self.send_to_kitsu)
                thread.start()
                self.progress_dialog.setText('Uploading to Kitsu... please wait...')
                self.progress_dialog.update(80)
                thread.join()

                self.progress_dialog.setText('Setting preview file into database')
                self.progress_dialog.update(90)
                gazu.task.set_main_preview(self.preview_file) #  Set preview as asset thumbnail

                self.progress_dialog.setText('DONE !!!')
                self.progress_dialog.update(100)
            else:
                print('Invalid file path from the render function. \n\nself.render_function = None or False')

        def select_file(self):
            file_dialog = QFileDialog()
            file_dialog.setFileMode(QFileDialog.ExistingFile)
            file_dialog.setNameFilter("Video Files (*.mov *.mp4)")
            file_dialog.setViewMode(QFileDialog.Detail)

            file_path, _ = file_dialog.getOpenFileName(self, "Open Video File", "", "Video Files (*.mov *.mp4)")
            
            if file_path:
                self.ui.publish_file_path.setText(str(file_path))
                self.file_path = file_path
            

        def update_context_from_selection(self):

            project = gazu.project.get_project_by_name(self.ui.project_box.currentText())

            index = self.ui.treeView.selectedIndexes()[0]
            item = self.ui.treeView.model().itemFromIndex(index)
            
            parent = item
            context_list = []
            context_list.append({
                        'name': item.text(),
                        'id': item.toolTip()
                    })

            while parent != None:
                parent = parent.parent()
                if parent:
                    context_list.append({
                        'name': parent.text(),
                        'id': parent.toolTip()
                    })

            context_list.append({
                'name' : project['name'],
                'id' : project['id']
            })

            context_list.reverse()
            context = ''.join([' / '+ str(element['name']) for element in context_list])

            self.ui.context_text.setText(context)

            task_type = gazu.task.get_task_type_by_name(item.text())
            if task_type:
                # If its a task, enable the button to publish
                self.ui.publish_button.setEnabled(True)
                self.context = item.toolTip()
            else:
                self.ui.publish_button.setEnabled(False)
         
        def load_tree(self):
            project = gazu.project.get_project_by_name(self.ui.project_box.currentText())
            sequences = gazu.shot.all_sequences_for_project(project['id'])
            model = QStandardItemModel()

            if self.ui.showonlymine.isChecked():
                tasks = gazu.user.all_tasks_to_do()
                data = {}
                for task in tasks:
                    #nuke.tprint(self.ui.project_box.currentText(), task['project_name'])
                    if self.ui.project_box.currentText() == task['project_name']:
                        try:
                            data[task['sequence_name']]
                        except:
                            data[task['sequence_name']] = {}
                        try:
                            data[task['sequence_name']][task['entity_name']]
                        except:
                            data[task['sequence_name']][task['entity_name']] = []
                    
                        data[task['sequence_name']][task['entity_name']].append(task)
                
                #nuke.tprint(data)
                for sequence in  data:
                    item = QStandardItem(sequence)
                    model.appendRow(item)
                    for shot in data[sequence]:
                        shot_item = QStandardItem(str(shot))
                        item.appendRow(shot_item)
                        for task in data[sequence][shot]:
                            task_item = QStandardItem(str(task['task_type_name']))
                            task_item.setToolTip(str(task['id']))
                            shot_item.appendRow(task_item)
            else:
                
                for seq in sequences:
                    item = QStandardItem(str(seq['name']))
                    #item.setIcon(QIcon.fromTheme("folder"))

                    model.appendRow(item)

                    shots = gazu.shot.all_shots_for_sequence(seq)
                    for shot in shots:
                        shot_item = QStandardItem(str(shot['name']))
                        item.appendRow(shot_item)
                        tasks = gazu.task.all_tasks_for_shot(shot)
                        for task in tasks:
                            task_item = QStandardItem(str(task['task_type_name']))
                            task_item.setToolTip(str(task['id']))
                            shot_item.appendRow(task_item)

            

                
            self.ui.treeView.setModel(model)
    
    print('[ SUCCES !!! ] : Kitsu-connect-publisher')

except Exception as eee:
    print(str(eee))


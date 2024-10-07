import maya.cmds as cmds
import maya.mel as mel
import maya.OpenMayaUI as omui
import os, sys, tempfile, time


try:
    from PySide2 import QtWidgets, QtCore
    from PySide2.QtUiTools import QUiLoader
    from PySide2.QtCore import QFile
    print("Using PySide2")
except ImportError:
    try:
        from PySide6 import QtWidgets, QtCore
        from PySide6.QtUiTools import QUiLoader
        from PySide6.QtCore import QFile
        print("Using PySide6")
    except ImportError:
        raise ImportError("Neither PySide2 nor PySide6 is available.")

user_script_folder = cmds.internalVar(userScriptDir=True)
kitsu_path = os.path.join(os.path.dirname(os.path.dirname(user_script_folder)), 'prefs','shelves','kitsu-connect')
sys.path.append(kitsu_path)
sys.path.append(os.path.join(kitsu_path, 'site-packages'))


from settings import Kitsu_Settings
import gazu

class KitsuItem(QtWidgets.QTreeWidgetItem):
    def __init__(self, parent, text, id=None):
        """
        Custom QTreeWidgetItem that holds an additional ID attribute.
        
        Args:
            parent (QTreeWidgetItem or QTreeWidget): Parent item or tree widget.
            text (str): Display text of the item.
            id (str, optional): Unique ID associated with the item.
        """
        super(KitsuItem, self).__init__(parent, [text])  # Initialize the QTreeWidgetItem with the text
        self.ID = id  # Store the unique ID

    def get_id(self):
        """Return the unique ID of this item."""
        return self.ID

class publish_playblast_window(QtWidgets.QMainWindow):
    def __init__(self):
        super(publish_playblast_window, self).__init__()

        self.ui_file = os.path.join(kitsu_path, 'ui','publisher.ui') 
        self.context_id = None
        # Load the .ui file
        self.load_ui(self.ui_file)
        self.settings = Kitsu_Settings()
        self.settings.check_connection()
        self.populate_tasks()
        self.ui.publish_button.setEnabled(False)
        
        self.ui.task_tree.itemDoubleClicked.connect(self.set_context)
        self.ui.publish_button.released.connect(self.publish_playblast)

    def populate_tasks(self):
        tasks = gazu.user.all_tasks_to_do()
        
        data = {}
        for task in tasks:
            type = task['task_type_for_entity']
            if type not in data:
                data[type] = {}
                
            if type == 'Asset':
                sequence = task['sequence_name']
                if task['entity_name'] not in data[type]:
                    data[type][task['entity_name']] = []
                
                if task['task_type_name'] not in data[type][task['entity_name']]:
                    data[type][task['entity_name']].append({'name': task['task_type_name'],'id': task['id']})
            else:
                sequence = task['sequence_name']
                if sequence not in data[type]:
                    data[type][sequence] = {}
                    
                if task['entity_name'] not in data[type][sequence]:
                    data[type][sequence][task['entity_name']] = []
                
                if task['task_type_name'] not in data[type][sequence][task['entity_name']]:
                    data[type][sequence][task['entity_name']].append({'name': task['task_type_name'],'id': task['id']})

        self.ui.task_tree.clear()

         # Iterate through the dictionary and add items to the tree widget
        for category, sub_categories in data.items():
            # Create top-level item for each category (e.g., 'Asset' or 'Shot')
            category_item = KitsuItem(self.ui.task_tree, text=category)
    
            for sub_category_name, sub_category_value in sub_categories.items():
                # Create sub-category items under the category (e.g., entity name for 'Asset' or sequence name for 'Shot')
                sub_category_item = KitsuItem(category_item, text=sub_category_name)
    
                # Check if `sub_category_value` is a dictionary (e.g., for 'Shot') or a list (e.g., for 'Asset')
                if isinstance(sub_category_value, dict):
                    # Iterate through shot items in the sequence
                    for shot_name, tasks in sub_category_value.items():
                        shot_item = KitsuItem(sub_category_item, text=shot_name)
    
                        # `tasks` is a list of task dictionaries, so iterate through it
                        for task in tasks:
                            task_item = KitsuItem(shot_item, text=task['name'], id=task['id'])
                elif isinstance(sub_category_value, list):
                    # Directly iterate through tasks in the list (e.g., for 'Asset')
                    for task in sub_category_value:
                        task_item = KitsuItem(sub_category_item, text=task['name'], id=task['id'])

        
    def set_context(self,item,column):
        if item.ID:
            self.context_id = item.ID
            self.ui.context_id.setText(item.ID)
            self.ui.publish_button.setEnabled(True)
        else:
            self.context_id = None
            self.ui.context_id.setText(item.ID)
            self.ui.publish_button.setEnabled(False)
        
        
    def load_ui(self, ui_file):
        loader = QUiLoader()
        path = QFile(ui_file)
        path.open(QFile.ReadOnly)
        self.ui = loader.load(path, self)
        path.close()


    def create_playblast_in_temp(self):
        # Get the current scene name (without extension)
        scene_name = cmds.file(q=True, sceneName=True, shortName=True).rsplit(".", 1)[0]
        
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Set the output file name with a timestamp to ensure uniqueness
        timestamp = int(time.time())
        output_file = os.path.join(temp_dir, f"{scene_name}_playblast_{timestamp}")
        
        # Get the current time slider range
        start_frame = cmds.playbackOptions(q=True, minTime=True)
        end_frame = cmds.playbackOptions(q=True, maxTime=True)
        
        # Try to create the playblast
        try:
            playblast_file = cmds.playblast(
                filename=output_file+'.mov',
                format="qt",
                compression="H.264",
                quality=100,
                width=1920,
                height=1080,
                showOrnaments=False,
                startTime=start_frame,
                endTime=end_frame,
                viewer=False,
                percent=100,
                clearCache=True,
                offScreen=True
            )
            print(f"Playblast created successfully: {playblast_file}")
            return playblast_file
        except RuntimeError as e:
            print(f"Error creating playblast: {str(e)}")
            print("Trying alternative method...")
            
            # Try an alternative method using a different format
            try:
                playblast_file = cmds.playblast(
                    filename=output_file+'.avi',
                    format="avi",
                    compression="none",
                    quality=100,
                    width=1920,
                    height=1080,
                    showOrnaments=False,
                    startTime=start_frame,
                    endTime=end_frame,
                    viewer=False,
                    percent=100,
                    clearCache=True,
                    offScreen=True
                )
                print(f"Playblast created successfully with alternative method: {playblast_file}")
                return playblast_file
            except Exception as e:
                print(f"Alternative method also failed: {str(e)}")
                return None

    def show_message_box(self, title, message, button_labels=None):
        """
        Display a message box in Maya.
        
        Args:
        title (str): The title of the message box.
        message (str): The main message to display.
        button_labels (list): Optional list of button labels. Defaults to ["OK"].
        
        Returns:
        str: The label of the button that was clicked.
        """
        if button_labels is None:
            button_labels = ["OK"]
        
        result = cmds.confirmDialog(
            title=title,
            message=message,
            button=button_labels,
            defaultButton=button_labels[0],
            cancelButton=button_labels[-1],
            dismissString=button_labels[-1]
        )
        
        return result

    def publish_playblast(self):
        try:

            playblast_file = self.create_playblast_in_temp()

            status = gazu.task.get_task_status_by_short_name("wfa")
            task = gazu.task.get_task(self.context_id)
            file_string = '\n\n<hr><b><u>SCENE FILE :\n</b></u><i>' + str(cmds.file(query=True, sceneName=True))+ '\n\n</i><b><u>FILE :</b></u><i>\n' + str(playblast_file) + '</i>\n'
            comment = gazu.task.add_comment(task, status, self.ui.comment_box.toPlainText()+file_string)

            preview_file = gazu.task.add_preview(
                    task,
                    comment,
                    playblast_file
                )

            # Remove the temporary playblast file
            if os.path.exists(playblast_file):
                os.remove(playblast_file)
                print(f"Temporary playblast file deleted: {playblast_file}")
            else:
                print("Temporary playblast file not found.")

            
            self.show_message_box("Succes", "Submitted to kitsu !")
            return True
        except Exception as eee:
            self.show_message_box("Information", "Failed to Submit : "+ str(eee))
            return False



 
    


import maya.cmds as cmds
import os, sys, json
import maya.OpenMayaUI as omui

user_script_folder = cmds.internalVar(userScriptDir=True)
kitsu_path = os.path.join(os.path.dirname(os.path.dirname(user_script_folder)), 'prefs','shelves','kitsu-connect')
sys.path.append(kitsu_path)
sys.path.append(os.path.join(kitsu_path, 'site-packages'))

import gazu 


# Try to import PySide2 and shiboken2 first, if not available, fallback to PySide6 and shiboken6
try:
    from PySide2 import QtWidgets, QtCore
    import shiboken2 as shiboken
    print("Using PySide2 and shiboken2")
except ImportError:
    try:
        from PySide6 import QtWidgets, QtCore
        import shiboken6 as shiboken
        print("Using PySide6 and shiboken6")
    except ImportError:
        raise ImportError("Neither PySide2/shiboken2 nor PySide6/shiboken6 is available.")


# Function to get the Maya main window as a QWidget
def get_maya_main_window():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return shiboken.wrapInstance(int(main_window_ptr), QtWidgets.QWidget)


# Create the main window class
class KitsuLoginWindow(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(KitsuLoginWindow, self).__init__(parent)

        self.user_config_file = os.path.join(kitsu_path, 'user_conf.json')
        print(self.user_config_file)

        # Set window title and size
        self.setWindowTitle("Kitsu Login")
        self.setFixedSize(300, 150)

        # Create the form layout
        self.layout = QtWidgets.QFormLayout(self)
        self.data = {}

        # Create input fields
        self.kitsu_url = QtWidgets.QLineEdit()
        self.kitsu_url.setPlaceholderText("https://kitsu.example.com")
        self.username = QtWidgets.QLineEdit()
        self.username.setPlaceholderText("Username")
        self.password = QtWidgets.QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)  # Hide password input

        # Create the submit button
        self.submit_button = QtWidgets.QPushButton("Save")
        self.submit_button.clicked.connect(self.submit_credentials)

        # Add input fields to the form layout
        self.layout.addRow("Kitsu URL:", self.kitsu_url)
        self.layout.addRow("Username:", self.username)
        self.layout.addRow("Password:", self.password)
        self.layout.addRow(self.submit_button)

    def submit_credentials(self):
        data = {
            "url": self.kitsu_url.text(),
            "user": self.username.text(),
            "pwd": self.password.text()
        }

        try:
            gazu.client.set_host(data['url']+'/api')
            gazu.log_in(data['user'], data['pwd'])

            # Write the dictionary to the JSON file
            with open(self.user_config_file, 'w') as json_file:
                json.dump(data, json_file, indent=4)

            # Close the dialog after submission
            self.data = data
            self.accept()
        except Exception as eee:
            print(data, 'invalid', str(eee))
		
# Check if window is already open and close it
class Kitsu_Settings:
    def __init__(self):
        self.user_script_folder = cmds.internalVar(userScriptDir=True)
        self.user_config_file = os.path.join(kitsu_path ,'user_conf.json')

        self.user = None
        self.url = None
        self.passwd = None

    def check_connection(self):
        # Check if the file exists
        if not os.path.isfile(self.user_config_file):
            self.show_kitsu_login_window()
        else:
            with open(self.user_config_file, 'r') as json_file:
                data = json.load(json_file)
            try:
                gazu.client.set_host(data['url']+'/api')
                gazu.log_in(data['user'], data['pwd'])
                return True
            except:
                self.show_kitsu_login_window()
        

    def show_kitsu_login_window(self):
        try:
            for widget in QtWidgets.QApplication.topLevelWidgets():
                if isinstance(widget, KitsuLoginWindow):
                    widget.close()
        except Exception as e:
            print(f"Error closing existing window: {e}")

        # Show the login window
        maya_main_window = get_maya_main_window()
        window = KitsuLoginWindow(parent=maya_main_window)
        window.exec_()
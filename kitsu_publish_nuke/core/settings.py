
print('IMPORTING : Kitsu-connect-settings')

try:
    import gazu
    import json
    import os

    from PySide2.QtCore import QFile, Qt
    from PySide2.QtWidgets import QApplication, QMainWindow, QWidget, QFormLayout, QMessageBox
    from PySide2.QtUiTools import QUiLoader
    from PySide2.QtGui import QStandardItem, QStandardItemModel, QIcon

    folder_path = os.path.dirname(os.path.dirname(__file__))
    
    class KitsuConnectSettings(QMainWindow):
        def __init__(self, parent=None):
            QMainWindow.__init__(self, parent)
            self.setWindowFlags(Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
            self.setWindowTitle("Kitsu Connect - Settings")
            # Load the UI file directly
            ui_file = os.path.join(folder_path, "ui", 'settings.ui')
            self.settings_json = os.path.join(folder_path,'settings.json')
            loader = QUiLoader()
            self.ui = loader.load(ui_file, self)
            self.ui.save_settings_button.clicked.connect(self.save_settings)

            self.settings = self.load_settings()

            self.connection = self.check_connection(self.settings)

            
        def check_connection(self, dict_data):
            try:
                gazu.client.set_host(dict_data['Kitsu API adress'])
                gazu.log_in(dict_data['Username'], dict_data['Password'])
                return True
            except Exception as eee:
                return str(eee)

        def load_settings(self):
            if os.path.exists(self.settings_json):
                # File exists, so open and read it
                try:
                    with open(self.settings_json, 'r') as file:
                        # Load the JSON data into a dictionary
                        data_dict = json.load(file)
                        # Now 'data_dict' contains your JSON data as a dictionary
                except:
                    print('Invalid kitsu settings')

                if data_dict:
                    layout = self.ui.settings_form_layout
                    for key in data_dict:
                         for row in range(layout.rowCount()):
                            label_item = layout.itemAt(row, QFormLayout.LabelRole)
                            field_item = layout.itemAt(row, QFormLayout.FieldRole)

                            if label_item and label_item.widget():
                                if field_item and field_item.widget():
                                    if label_item.widget().text() == key:
                                        field_item.widget().setText(data_dict[key])
                    return data_dict

            else:
                print(f"The file '{self.settings_json}' does not exist.")

        def save_settings(self):
            data_dict = {}
            layout = self.ui.settings_form_layout
            for row in range(layout.rowCount()):
                label_item = layout.itemAt(row, QFormLayout.LabelRole)
                field_item = layout.itemAt(row, QFormLayout.FieldRole)

                if label_item and label_item.widget():
                    print("Label Widget:", label_item.widget())
                    if field_item and field_item.widget():
                        data_dict[label_item.widget().text()] = field_item.widget().text()

            # Write the dictionary to the JSON file
            with open(self.settings_json, 'w') as file:
                json.dump(data_dict, file, indent=4)

            print('Settings Saved !!!')
            connection_status = self.check_connection(data_dict)
            
            if connection_status == True:
                self.close()
            else:
                dlg = QMessageBox(self)
                dlg.setWindowTitle("Kitsu Connect - Error")
                dlg.setText("Cannot connect to the server with these informations.\n\nPlease make certain you have a proper username and password\nand that the server field looks like : https://url_to_kitsu_site/api\n\nError :\n"+connection_status)
                button = dlg.exec_()
                if button == QMessageBox.Ok:
                    print("OK!")


    
    print('[ SUCCES !!! ] : Kitsu-connect-settings')

except Exception as eee:
    print(str(eee))



print('\n\n----------------------------')
print('     NUKE KITSU-CONNECT     ')
print('----------------------------\n\n')

import os, sys
import tempfile

folder_path = os.path.dirname(__file__)
path = os.path.join(folder_path, "site-packages")
sys.path.append(path)
nuke_publisher=None

try:
    import nuke
    from nukescripts import panels

    from core import publisher

    #panels.registerWidgetAsPanel('KitsuConnect', 'Kitsu Connect 1.0', 'uk.co.thefoundry.KitsuConnect')

    def kitsu_render_preview():

        if nuke.selectedNodes():

            node = nuke.selectedNodes()[0]
            write_node = nuke.createNode('Write')

            # Set the file path and settings for the Write node (modify these according to your requirements)

            # first we doa temp file
            temp_dir = tempfile.mkdtemp()
            output_file_path = os.path.join(temp_dir, 'kitsu_preview.mov')
            output_file_path = output_file_path.replace(os.sep, '/')

            # we set all the settings

            write_node['file'].setValue(output_file_path)
            #write_node['file_type'].setValue('mov')
            write_node['mov64_codec'].setValue(11)
            write_node['mov_prores_codec_profile'].setValue(4)
            write_node['create_directories'].setValue(True)
            
            if nuke.root()['OCIO_config'].value() != 'nuke-default':
                if nuke.root()['colorManagement'].value() == 'OCIO':
                    write_node['colorspace'].setValue('matte_paint')
                

            # connect and place the nodes

            write_node.setInput(0, node)
          
            write_node.setXpos(node.xpos())
            write_node.setYpos(node.ypos() + 80)
            
            first_frame = nuke.Root()['first_frame'].value()
            last_frame = nuke.Root()['last_frame'].value()
            nuke.execute(write_node, int(first_frame), int(last_frame))
            nuke.delete(write_node)

        return output_file_path

    def nuke_kitsu_publisher():
        if nuke.selectedNodes():
            if 'Read' in nuke.selectedNodes()[0].Class():
                node = nuke.selectedNodes()[0]
                global nuke_publisher
                nuke_publisher = publisher.KitsuConnecPublisher()
                nuke_publisher.set_file_path(str(node['file'].getValue()))
                
                nuke_publisher.render_function = kitsu_render_preview
                nuke_publisher.show()

    def export_timeline():
        selection = hiero.ui.getTimelineEditor(hiero.ui.activeSequence()).selection()
        if selection:
            global studiowindow
            path = os.path.join(folder_path, "core")
            sys.path.append(path)
            import studio_export_timeline     
            studiowindow = studio_export_timeline.export_timeline()
            studiowindow.show()
        else:
            nuke.message('Please select the clip on the timeline you wish to send to Kitsu')


    # Create a new menu
    kitsu_menu = nuke.menu("Nuke").addMenu("Kitsu-connect")

    # Add menu items to the new menu
    if nuke.env['studio']:
        kitsu_menu.addCommand("Send Timeline Clips to Kitsu", export_timeline, 'Ctrl+p')
    else:
        kitsu_menu.addCommand("Publish", nuke_kitsu_publisher, 'Ctrl+p')
        
    from core import settings
    kitsu_menu.addCommand("Settings", settings.KitsuConnectSettings().show, 'Ctrl+Shift+p')


except Exception as eee:
    print(str(eee))


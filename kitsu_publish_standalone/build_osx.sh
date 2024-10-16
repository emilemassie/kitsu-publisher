pyinstaller --clean -y -n kitsu_publisher_standalone --windowed --onefile --icon=./icons/icon.png --add-data ./icons:icons --add-data ./ui:ui --add-data ./ffmpeg:. kitsu_publisher_standalone.py

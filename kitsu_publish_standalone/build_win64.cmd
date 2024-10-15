@ECHO ON
python -m PyInstaller --clean -y -n kitsu_publisher_standalone --noconsole --onefile --icon=./icons/icon.png --add-data ./icons:icons --add-data ./ui:ui --add-data ./dependencies/win/ffmpeg.exe;.  kitsu_publisher_standalone.py
pause
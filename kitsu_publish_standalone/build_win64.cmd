@ECHO ON
python -m PyInstaller --clean -y -n kitsu_publisher_standalone --noconsole --onedir --icon=./icons/icon.png --add-data ./icons:icons --add-data ./ui:ui --add-data ./ffmpeg_win:ffmpeg_win  kitsu_publisher_standalone.py
pause
from setuptools import setup

APP = ['kitsu_publisher_standalone.py']
DATA_FILES = ['./icons','./ui','./ffmpeg']
OPTIONS = {'iconfile': './icons/icon.png'}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app', 'requests', 'PyQt5', 'gazu', 'appdirs'],
)





# python3 build_osx.py py2app
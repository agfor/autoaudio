[app]

# title of your application
title = autoaudio

# project root directory. default = The parent directory of input_file
project_dir = .

# source file entry point path. default = main.py
input_file = C:\Users\adam\autoaudio\main.py

# directory where the executable output is generated
exec_directory = .

# path to the project file relative to project_dir
project_file = 

# application icon
icon = C:\Users\adam\autoaudio\.venv\Lib\site-packages\PySide6\scripts\deploy_lib\pyside_icon.ico

[python]

# python path
python_path = C:\Users\adam\autoaudio\.venv\Scripts\python.exe

# python packages to install
packages = Nuitka==2.7.11

# buildozer = for deploying Android application
android_packages = buildozer==1.5.0,cython==0.29.33

[qt]

# paths to required qml files. comma separated
# normally all the qml files required by the project are added automatically
# design studio projects include the qml files using qt resources
qml_files = 

# excluded qml plugin binaries
excluded_qml_plugins = 

# qt modules used. comma separated
modules = Gui,Widgets,Network,Core,Multimedia

# qt plugins used by the application. only relevant for desktop deployment
# for qt plugins used in android application see [android][plugins]
plugins = multimedia,platforms

[android]

# path to pyside wheel
wheel_pyside = 

# path to shiboken wheel
wheel_shiboken = 

# plugins to be copied to libs folder of the packaged application. comma separated
plugins = 

[nuitka]

# usage description for permissions requested by the app as found in the info.plist file
# of the app bundle. comma separated
# eg = extra_args = --show-modules --follow-stdlib
macos.permissions = 

# mode of using nuitka. accepts standalone or onefile. default = onefile
mode = onefile

# specify any extra nuitka arguments
extra_args = --no-progressbar --lto=yes --windows-console-mode=disable --python-flag=no_docstrings --python-flag=no_asserts --noinclude-dlls=*unicodedata* --noinclude-dlls=shiboken6/msvcp140*.dll --noinclude-qt-translations --noinclude-qt-plugins=imageformats --noinclude-qt-plugins=iconengines --noinclude-qt-plugins=tls --noinclude-dlls=opengl32sw.dll --noinclude-dlls=d3dcompiler_47.dll --noinclude-dlls=libssl-3-x64.dll --noinclude-dlls=libcrypto-3-x64.dll --noinclude-dlls=*/qdirect2d.dll --noinclude-dlls=*/qoffscreen.dll --noinclude-dlls=*/qminimal.dll --noinclude-dlls=*/ffmpegmediaplugin.dll --noinclude-dlls=avcodec-61.dll --noinclude-dlls=avformat-61.dll --noinclude-dlls=avutil-59.dll --noinclude-dlls=swscale-8.dll --noinclude-dlls=swresample-5.dll --noinclude-unittest-mode=nofollow --noinclude-pytest-mode=nofollow --nofollow-import-to=unittest,pdb,email,http,xmlrpc,ssl,ftplib,telnetlib,socketserver,html,xml,unicodedata,decimal,lzma,bz2,hashlib,multiprocessing,concurrent,asyncio,PySide6.QtPdf,PySide6.QtPdfWidgets,PySide6.QtWebEngine,PySide6.QtWebEngineWidgets,PySide6.QtWebEngineCore,PySide6.QtQml,PySide6.QtQuick,PySide6.Qt3DCore,PySide6.Qt3DRender,PySide6.QtCharts,PySide6.QtDataVisualization,PySide6.QtSvg,PySide6.QtSvgWidgets,PySide6.QtOpenGL,PySide6.QtOpenGLWidgets,PySide6.QtBluetooth,PySide6.QtNfc,PySide6.QtPositioning,PySide6.QtSensors,PySide6.QtSerialPort,PySide6.QtTest,PySide6.QtXml

[buildozer]

# build mode
# possible values = ["aarch64", "armv7a", "i686", "x86_64"]
# release creates a .aab, while debug creates a .apk
mode = debug

# path to pyside6 and shiboken6 recipe dir
recipe_dir = 

# path to extra qt android .jar files to be loaded by the application
jars_dir = 

# if empty, uses default ndk path downloaded by buildozer
ndk_path = 

# if empty, uses default sdk path downloaded by buildozer
sdk_path = 

# other libraries to be loaded at app startup. comma separated.
local_libs = 

# architecture of deployed platform
arch = 


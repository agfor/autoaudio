import json
import signal
import sys
import time
import traceback

from PySide6.QtCore import QDataStream, QEvent, QMetaMethod, QProcess, QTimer, Qt
from PySide6.QtGui import QAction
from PySide6.QtNetwork import QLocalSocket
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                                 QComboBox, QLineEdit, QCheckBox, QSystemTrayIcon,
                                 QMenu, QLabel, QStyle)

from router-multi import main

class AutoAudio(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app

        self.audio_process = QProcess()
        self.audio_process.readyReadStandardOutput.connect(self.print_subprocess)
        if "py" in sys.argv[0]:
            self.audio_process.start("uv", ["run", "python", "-u", "main.py", 'audio'])
        else:
            self.audio_process.start(sys.argv[0], ["audio"])
        if not self.audio_process.waitForStarted(5000):
            print("process not started")
        # get rid of this sleep and use the stdout pipe to detect when it's really up?
        # probably means we need to start the event loop first before showing the UI
        time.sleep(1)

        self.socket = QLocalSocket()
        self.socket.connectToServer("AutoAudioPipe")
        if not self.socket.waitForConnected(5000):
            print(self.socket.state(), self.socket.errorString())
            print("not connected")
        self.stream = QDataStream(self.socket)
        self.send_to_router({"command": "get_device_info"})
        if not self.socket.waitForBytesWritten(5000):
            print("not written")
        if not self.socket.waitForReadyRead(5000):
            print(self.socket.state(), self.socket.errorString())
            print("not readyread")
        self.stopping = False

        self.timer = QTimer()
        self.timer.timeout.connect(lambda: None)

        signal.signal(signal.SIGINT, lambda *args: self.closeEvent())
        sys.excepthook = lambda et, ev, tb: print("".join(traceback.format_exception(et, ev, tb)))

    def print_subprocess(self):
        print(self.audio_process.readAllStandardOutput().data().decode().strip())

    def start(self):
        self.setup_window()
        self.handle_response()

        if QSystemTrayIcon.isSystemTrayAvailable():
            self.setup_system_tray()
            self.app.setQuitOnLastWindowClosed(False)

        self.socket.readyRead.connect(self.handle_response)
        self.show()
        self.timer.start(500)
        self.app.exec()

    def handle_response(self):
        while not self.stream.atEnd():
            data = json.loads(self.stream.readString())
            print("received", data)
            if data.get("fallback"):
                self.update_ui(data)

    def update_ui(self, data):
        if self.input.isSignalConnected(QMetaMethod.fromSignal(self.input.currentTextChanged)):
            self.input.currentTextChanged.disconnect()
            self.primary.currentTextChanged.disconnect()
            self.primary_filter.returnPressed.disconnect()
            self.fallback.currentTextChanged.disconnect()

        self.input.clear()
        self.input.addItems(data["inputs"])
        self.input.setCurrentText(data["input"])
        self.primary.clear()
        self.primary.addItems(["Device not connected"] + data["outputs"])
        if data["primary"]:
            self.primary.setCurrentText(data["primary"])
        self.primary_filter.setText(data["primary_filter"])
        self.fallback.clear()
        self.fallback.addItems(data["outputs"])
        self.fallback.setCurrentText(data["fallback"])

        self.input.currentTextChanged.connect(self.ui_change)
        self.primary.currentTextChanged.connect(self.ui_change)
        self.primary_filter.returnPressed.connect(self.filter_changed)
        self.fallback.currentTextChanged.connect(self.ui_change)

    def send_to_router(self, data):
        print("sending", data)
        self.stream.writeString(json.dumps(data))
        self.socket.flush()

    def setup_window(self):
        self.setWindowTitle("AutoAudio")
        self.setMinimumSize(300, 200)

        icon = self.style().standardIcon(QStyle.SP_MediaVolume)
        self.setWindowIcon(icon)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        layout.addWidget(QLabel("Audio Input:"))
        self.input = QComboBox()
        layout.addWidget(self.input)

        layout.addWidget(QLabel("Primary Output:"))
        self.primary = QComboBox()
        layout.addWidget(self.primary)

        layout.addWidget(QLabel("Primary Output Filter (enter/return to change):"))
        self.primary_filter = QLineEdit()
        layout.addWidget(self.primary_filter)

        layout.addWidget(QLabel("Fallback Output:"))
        self.fallback = QComboBox()
        layout.addWidget(self.fallback)

        self.boost = QCheckBox("Volume Boost")
        layout.addWidget(self.boost)
        self.boost.stateChanged.connect(self.boost_changed)
        layout.addStretch()

    def ui_change(self, _ = None):
        self.send_to_router({"command": "ui_change",
                             "input": self.input.currentText(),
                             "fallback": self.fallback.currentText(),
                             "primary": self.primary.currentText(),
                             })

    def filter_changed(self):
        self.send_to_router({"command": "filter_changed", "primary_filter": self.primary_filter.text()})

    def boost_changed(self, state):
        self.send_to_router({"command": "set_boost", "enabled": bool(state)})

    def setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_MediaVolume))
        tray_menu = QMenu()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.closeEvent)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.showNormal()
            self.setWindowState(Qt.WindowActive)
            self.raise_()
            self.activateWindow()
            self.tray_icon.hide()

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange and self.windowState() & Qt.WindowMinimized:
            self.tray_icon.show()
            self.hide()

    def closeEvent(self, event = None):
        if not self.stopping:
            self.stopping = True
            self.send_to_router({"command": "shutdown"})
            self.socket.disconnectFromServer()
            self.audio_process.terminate()
            self.audio_process.waitForFinished(5000)
            QApplication.quit()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        main()
    else:
        app = QApplication([])
        auto_audio = AutoAudio(app)
        auto_audio.start()

import signal
import sys
import traceback

from PySide6.QtCore import QEvent, QMetaMethod, QTimer, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                                 QComboBox, QLineEdit, QCheckBox, QSystemTrayIcon,
                                 QMenu, QLabel, QStyle)

from router import AutoAudioRouter

class AutoAudio(QMainWindow):
    def __init__(self, router, app):
        super().__init__()
        self.router = router
        self.app = app

        self.router.setup()
        self.setup_window()
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.setup_system_tray()

        self.timer = QTimer()
        self.timer.timeout.connect(lambda: None)

        signal.signal(signal.SIGINT, lambda *args: self.closeEvent())
        sys.excepthook = lambda et, ev, tb: print("".join(traceback.format_exception(et, ev, tb)))

    def start(self):
        self.router.devices_changed.connect(self.update_ui)
        self.router.start()
        self.show()
        self.timer.start(500)
        self.app.exec()

    def update_ui(self):
        if self.input.isSignalConnected(QMetaMethod.fromSignal(self.input.currentTextChanged)):
            self.input.currentTextChanged.disconnect()
            self.primary.currentTextChanged.disconnect()
            self.primary_filter.returnPressed.disconnect()
            self.fallback.currentTextChanged.disconnect()

        self.input.clear()
        self.input.addItems([d.description() for d in self.router.media_devices.audioInputs()])
        self.input.setCurrentText(self.router.input_device.description())
        outputs = [d.description() for d in self.router.media_devices.audioOutputs()]
        self.primary.clear()
        self.primary.addItems(["Device not connected"] + outputs)
        if self.router.primary_device:
            self.primary.setCurrentText(self.router.primary_device.description())
        self.primary_filter.setText(self.router.primary_filter)
        self.fallback.clear()
        self.fallback.addItems(outputs)
        self.fallback.setCurrentText(self.router.fallback_device.description())

        self.input.currentTextChanged.connect(self.ui_change)
        self.primary.currentTextChanged.connect(self.ui_change)
        self.primary_filter.returnPressed.connect(self.filter_changed)
        self.fallback.currentTextChanged.connect(self.ui_change)

    def setup_window(self):
        self.setWindowTitle("AutoAudio")
        self.setMinimumSize(300, 200)

        icon = self.style().standardIcon(QStyle.SP_MediaVolume)
        self.setWindowIcon(icon)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        layout.addWidget(QLabel("Audio Source:"))
        self.input = QComboBox()
        layout.addWidget(self.input)

        layout.addWidget(QLabel("Primary Output:"))
        self.primary = QComboBox()
        layout.addWidget(self.primary)

        layout.addWidget(QLabel("Primary Output Name (enter/return to change):"))
        self.primary_filter = QLineEdit()
        layout.addWidget(self.primary_filter)

        layout.addWidget(QLabel("Fallback Output:"))
        self.fallback = QComboBox()
        layout.addWidget(self.fallback)

        self.boost = QCheckBox("Volume Boost")
        self.boost.stateChanged.connect(self.boost_changed)
        layout.addWidget(self.boost)
        layout.addStretch()

    def ui_change(self):
        if self.input.currentText() != self.router.input_device.description():
            self.router.input_filter = self.input.currentText()
        if self.fallback.currentText() != self.router.fallback_device.description():
            self.router.fallback_filter = self.fallback.currentText()

        primary_text = self.primary.currentText()
        if primary_text != "Device not connected" and not (self.router.primary_device and primary_text == self.router.primary_device.description()):
            self.router.primary_filter = primary_text
        self.router.detect_device()

    def filter_changed(self):
        self.router.primary_filter = self.primary_filter.text()
        self.router.detect_device()

    def boost_changed(self, state):
        self.router.boost = bool(state)

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
        self.router.stop()
        QApplication.quit()

if __name__ == '__main__':
    app = QApplication([])
    if QSystemTrayIcon.isSystemTrayAvailable():
        app.setQuitOnLastWindowClosed(False)

    router = AutoAudioRouter()
    auto_audio = AutoAudio(router, app)
    auto_audio.start()

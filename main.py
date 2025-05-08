from PySide6.QtCore import QEvent, QMetaMethod, QTimer, Qt, QThread, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                                 QComboBox, QLineEdit, QCheckBox, QSystemTrayIcon,
                                 QMenu, QLabel, QStyle)

from router import AutoAudioRouter

class AutoAudio(QMainWindow):
    input_changed = Signal(str)
    primary_changed = Signal(str)
    fallback_changed = Signal(str)
    boost_state_changed = Signal(bool)

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.thread = QThread()
        self.router = AutoAudioRouter()
        self.router.moveToThread(self.thread)
        self.device_info = None

        self.input_changed.connect(self.router.set_input_filter)
        self.primary_changed.connect(self.router.set_primary_filter)
        self.fallback_changed.connect(self.router.set_fallback_filter)
        self.boost_state_changed.connect(self.router.set_boost)

        self.setup_window()
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.app.setQuitOnLastWindowClosed(False)
            self.setup_system_tray()

        self.timer = QTimer()
        self.timer.timeout.connect(lambda: None)

    def start(self):
        self.router.devices_changed.connect(self.update_ui)
        self.thread.started.connect(self.router.run)
        self.thread.finished.connect(self.router.stop)
        self.thread.start()
        self.timer.start(500)
        self.app.exec()

    def update_ui(self, device_info):
        if not self.isVisible():
            self.show()

        self.device_info = device_info
        if self.input.isSignalConnected(QMetaMethod.fromSignal(self.input.currentTextChanged)):
            self.input.currentTextChanged.disconnect()
            self.primary.currentTextChanged.disconnect()
            self.primary_filter.returnPressed.disconnect()
            self.fallback.currentTextChanged.disconnect()

        self.input.clear()
        self.input.addItems(device_info['input_devices'])
        self.input.setCurrentText(device_info['input_device'])
        self.primary.clear()
        self.primary.addItems(["Device not connected"] + device_info['output_devices'])
        if device_info['primary_device']:
            self.primary.setCurrentText(device_info['primary_device'])
        self.primary_filter.setText(device_info['primary_filter'])
        self.fallback.clear()
        self.fallback.addItems(device_info['output_devices'])
        self.fallback.setCurrentText(device_info['fallback_device'])

        self.input.currentTextChanged.connect(self.ui_change)
        self.primary.currentTextChanged.connect(self.ui_change)
        self.primary_filter.returnPressed.connect(self.filter_changed)
        self.fallback.currentTextChanged.connect(self.ui_change)

    def ui_change(self):
        if not self.device_info:
            return

        if self.input.currentText() != self.device_info['input_device']:
            self.input_changed.emit(self.input.currentText())
        if self.fallback.currentText() != self.device_info['fallback_device']:
            self.fallback_changed.emit(self.fallback.currentText())

        if self.primary.currentText() not in ("Device not connected", self.device_info['primary_device']):
            self.primary_changed.emit(self.primary.currentText())

    def filter_changed(self):
        self.primary_changed.emit(self.primary_filter.text())

    def boost_changed(self, state):
        self.boost_state_changed.emit(bool(state))

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
        self.timer.stop()
        self.thread.quit()
        self.thread.wait()
        QApplication.quit()

if __name__ == '__main__':
    import signal
    import sys
    import traceback

    app = QApplication([])
    auto_audio = AutoAudio(app)
    signal.signal(signal.SIGINT, lambda *args: auto_audio.closeEvent())
    sys.excepthook = lambda et, ev, tb: print("".join(traceback.format_exception(et, ev, tb)))
    auto_audio.start()

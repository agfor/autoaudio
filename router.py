import numpy as np
from PySide6.QtCore import QObject, Signal
from PySide6.QtMultimedia import QAudio, QAudioFormat, QAudioSink, QAudioSource, QMediaDevices

class AutoAudioRouter(QObject):
    devices_changed = Signal(dict)

    def __init__(self, boost = False):
        super().__init__()
        self.boost = boost
        self.stopped = False
        self.peak_history = np.zeros(1000, dtype=np.int16)
        self.history_index = 0
        self.input_filter = "Virtual Audio Cable"
        self.fallback_filter = "Speakers"
        self.primary_filter = "Headphones"
        self.data = bytes()
        self.sink = self.source = self.primary_device = self.fallback_device = self.input_device = None

    def set_input_filter(self, filter):
        self.input_filter = filter
        self.detect_device()

    def set_fallback_filter(self, filter):
        self.fallback_filter = filter
        self.detect_device()

    def set_primary_filter(self, filter):
        self.primary_filter = filter
        self.detect_device()

    def set_boost(self, boost):
        self.boost = boost

    def build_sink(self, device):
        if self.sink:
            self.sink.stateChanged.disconnect()
            self.sink.stop()
        self.sink = QAudioSink(device, self.format, parent=self)
        self.outstream = self.sink.start()
        self.sink.stateChanged.connect(self.sink_changed)

    def build_source(self):
        if self.source:
            self.source.stateChanged.disconnect()
            self.source.stop()
        self.source = QAudioSource(self.input_device, self.format, parent=self)
        self.instream = self.source.start()
        self.instream.readyRead.connect(self.process_input)
        self.source.stateChanged.connect(self.source_changed)

    def detect_device(self):
        input_devices = self.media_devices.audioInputs()
        input_device = self.find_device(input_devices, self.input_filter)
        if input_device != self.input_device:
            print("Input device changed:", input_device.description())
            self.input_device = input_device
            self.build_source()
        output_devices = self.media_devices.audioOutputs()
        fallback_device = self.find_device(output_devices, self.fallback_filter)
        primary_device = self.find_device(output_devices, self.primary_filter)
        if fallback_device != self.fallback_device:
            print("Fallback device changed:", fallback_device.description())
            self.fallback_device = fallback_device
            if not primary_device:
                print("Primary device not connected")
                self.build_sink(self.fallback_device)
        if primary_device != self.primary_device:
            self.primary_device = primary_device
            if primary_device:
                print("Primary device changed:", primary_device.description())
                self.build_sink(self.primary_device)
            else:
                print("Primary device not connected")
                self.build_sink(self.fallback_device)

        device_info = {
            'input_devices': [d.description() for d in input_devices],
            'output_devices': [d.description() for d in output_devices],
            'input_device': self.input_device.description() if self.input_device else "None",
            'primary_device': self.primary_device.description() if self.primary_device else "None",
            'fallback_device': self.fallback_device.description() if self.fallback_device else "None",
            'primary_filter': self.primary_filter
        }
        self.devices_changed.emit(device_info)

    def sink_changed(self, state: QAudio.State):
        if not (state == QAudio.State.ActiveState or self.stopped):
            self.build_sink(self.primary_device or self.fallback_device)

    def source_changed(self, state: QAudio.State):
        if not (state == QAudio.State.ActiveState or self.stopped):
            self.build_source()

    def find_device(self, devices, filter):
        return next((d for d in devices if filter in d.description()), None)

    def run(self):
        self.media_devices = QMediaDevices(parent=self)
        self.format = QAudioFormat(parent=self)
        self.format.setSampleRate(48000)
        self.format.setChannelCount(2)
        self.format.setSampleFormat(QAudioFormat.Int16)
        self.detect_device()
        self.media_devices.audioOutputsChanged.connect(self.detect_device)

    def stop(self):
        self.stopped = True
        self.source.stop()
        self.sink.stop()

    def process_input(self):
        self.outstream.write(self.data)
        self.data = self.instream.read(32000)
        if self.boost:
            np_data = np.frombuffer(self.data, dtype=np.int16)
            self.peak_history[self.history_index] = np.max(np.abs(np_data))
            self.history_index = (self.history_index + 1) % 1000
            peak_level = np.max(self.peak_history)
            actual_gain = 32767 / peak_level if peak_level > 10369 else 3.16
            self.data = (np_data * actual_gain).astype(np.int16).tobytes()

if __name__ == '__main__':
    import signal
    import sys
    import traceback

    from PySide6.QtCore import QThread, QCoreApplication, QTimer

    app = QCoreApplication()
    thread = QThread()
    router = AutoAudioRouter()
    router.moveToThread(thread)
    thread.started.connect(router.run)
    thread.finished.connect(router.stop)
    thread.start()

    timer = QTimer()
    timer.timeout.connect(lambda: None)

    def cleanup():
        timer.stop()
        thread.quit()
        thread.wait()

    app.aboutToQuit.connect(cleanup)
    signal.signal(signal.SIGINT, lambda *args: app.quit())
    sys.excepthook = lambda et, ev, tb: print("".join(traceback.format_exception(et, ev, tb)))
    timer.start(500)
    app.exec()

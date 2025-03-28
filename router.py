import numpy as np

from PySide6.QtCore import QObject, Signal
from PySide6.QtMultimedia import QAudio, QAudioFormat, QAudioSink, QAudioSource, QMediaDevices

class AutoAudioRouter(QObject):
    devices_changed = Signal()

    def __init__(self, boost = False):
        super().__init__()
        self.boost = boost
        self.peak_history = np.zeros(1000, dtype=np.int16)
        self.history_index = 0
        self.input_filter = "Virtual Audio Cable"
        self.fallback_filter = "Speakers"
        self.primary_filter = "Headphones"

    def detect_device(self):
        sink = self.sink
        source = self.source
        input_device = self.find_device(self.media_devices.audioInputs(), self.input_filter)
        if input_device != self.input_device:
            print("Input device changed")
            self.input_device = input_device
            self.source = QAudioSource(self.input_device, self.format)
            if source:
                source.stateChanged.disconnect()
                source.stop()
            self.instream = self.source.start()
            self.source.stateChanged.connect(self.source_changed)
            self.instream.readyRead.connect(self.process_input)
        output_devices = self.media_devices.audioOutputs()
        fallback_device = self.find_device(output_devices, self.fallback_filter)
        primary_device = self.find_device(output_devices, self.primary_filter)
        if fallback_device != self.fallback_device:
            print("Fallback device changed")
            self.fallback_device = fallback_device
            if not primary_device:
                print("Playing with fallback device")
                self.sink = QAudioSink(self.fallback_device, self.format)
                self.outstream = self.sink.start()
                self.sink.stateChanged.connect(self.sink_changed)
                if sink:
                    sink.stateChanged.disconnect()
                    sink.stop()
        if primary_device != self.primary_device:
            print("Primary device changed")
            self.primary_device = primary_device
            if primary_device:
                print("Playing with primary device")
                self.sink = QAudioSink(self.primary_device, self.format)
            else:
                print("Playing with fallback device")
                self.sink = QAudioSink(self.fallback_device, self.format)
            self.outstream = self.sink.start()
            self.sink.stateChanged.connect(self.sink_changed)
            if sink:
                sink.stateChanged.disconnect()
                sink.stop()
        self.devices_changed.emit()

    def sink_changed(self, state: QAudio.State):
        if state != QAudio.State.ActiveState:
            self.sink.stateChanged.disconnect()
            self.sink.stop()
            self.sink = QAudioSink(self.fallback_device, self.format)
            self.outstream = self.sink.start()
            self.sink.stateChanged.connect(self.sink_changed)

    def source_changed(self, state: QAudio.State):
        if state != QAudio.State.ActiveState:
            self.source.stateChanged.disconnect()
            self.source.stop()
            self.source = QAudioSource(self.input_device, self.format)
            self.instream = self.source.start()
            self.source.stateChanged.connect(self.source_changed)
            self.instream.readyRead.connect(self.process_input)

    def find_device(self, devices, filter):
        return next((d for d in devices if filter in d.description()), None)

    def setup(self):
        self.media_devices = QMediaDevices()
        self.format = QAudioFormat()
        self.format.setSampleRate(48000)
        self.format.setChannelCount(2)
        self.format.setSampleFormat(QAudioFormat.Int16)
        self.sink = self.source = self.primary_device = self.fallback_device = self.input_device = None

    def start(self):
        self.detect_device()
        self.media_devices.audioOutputsChanged.connect(self.detect_device)

    def stop(self):
        self.source.stop()
        self.sink.stop()

    def process_input(self):
        if self.boost:
            data = np.frombuffer(self.instream.read(4096), dtype=np.int16)

            self.peak_history[self.history_index] = np.max(np.abs(data))
            self.history_index = (self.history_index + 1) % 1000
            peak_level = np.max(self.peak_history)
            actual_gain = 32767 / peak_level if peak_level > 10369 else 3.16

            processed_data = (data * actual_gain).astype(np.int16).tobytes()
        else:
            processed_data = self.instream.read(4096)

        self.outstream.write(processed_data)

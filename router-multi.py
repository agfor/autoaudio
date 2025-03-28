import json
import signal
import sys
import traceback

import numpy as np

from PySide6.QtCore import QCoreApplication, QDataStream, QObject
from PySide6.QtMultimedia import QMediaDevices, QAudioSource, QAudioSink, QAudioFormat
from PySide6.QtNetwork import QLocalServer

class AutoAudioRouter(QObject):
    def __init__(self, boost = False):
        super().__init__()
        self.boost = boost
        self.peak_history = np.zeros(1000, dtype=np.int16)
        self.history_index = 0
        self.input_filter = "Virtual Audio Cable"
        self.fallback_filter = "Speakers"
        self.primary_filter = "Headphones"
        self.server = QLocalServer()
        self.server.listen("AutoAudioPipe")
        self.server.newConnection.connect(self.handle_connection)
        self.socket = self.stream = None

    def handle_connection(self):
        self.socket = self.server.nextPendingConnection()
        self.stream = QDataStream(self.socket)
        self.socket.readyRead.connect(self.handle_command)
        print("started")

    def handle_command(self):
        while not self.stream.atEnd():
            raw_data = self.stream.readString()
            if not raw_data:
                print("empty data received")
                return
            print("received", raw_data)
            data = json.loads(raw_data)
            command = data.get("command")

            match command:
                case "ui_change":
                    self.input_filter = data["input"]
                    self.fallback_filter = data["fallback"]
                    if data["primary"] != "Device not connected":
                        self.primary_filter = data["primary"]
                    self.detect_device()
                case "filter_changed":
                    self.primary_filter = data["primary_filter"]
                    self.detect_device()
                case "set_boost":
                    self.boost = data["enabled"]
                    self.send_device_info()
                case "get_device_info":
                    self.send_device_info()
                case "shutdown":
                   self.stop()

    def send_device_info(self):
        self.send_response({"inputs": [d.description() for d in self.media_devices.audioInputs()],
                            "input": self.input_device.description(),
                            "outputs": [d.description() for d in self.media_devices.audioOutputs()],
                            "fallback": self.fallback_device.description(),
                            "primary": self.primary_device.description() if self.primary_device else "",
                            "primary_filter": self.primary_filter,
                            })

    def send_response(self, data):
        if self.socket and self.stream:
            print("sending", data)
            self.stream.writeString(json.dumps(data))
            self.socket.flush()

    def detect_device(self):
        sink = self.sink
        source = self.source
        input_device = self.find_device(self.media_devices.audioInputs(), self.input_filter)
        if input_device != self.input_device:
            print("Input device changed")
            self.input_device = input_device
            self.source = QAudioSource(self.input_device, self.format)
            if source: source.stop()
            self.instream = self.source.start()
            self.instream.readyRead.connect(self.process_input)
            self.source.stateChanged.connect(self.detect_device)
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
                if sink: sink.stop()
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
            if sink: sink.stop()
        self.send_device_info()

    def find_device(self, devices, filter):
        return next((d for d in devices if filter in d.description()), None)

    def setup(self):
        self.media_devices = QMediaDevices()
        self.format = QAudioFormat()
        self.format.setSampleRate(48000)
        self.format.setChannelCount(2)
        self.format.setSampleFormat(QAudioFormat.Int16)
        self.sink = self.source = self.primary_device = self.fallback_device = self.input_device = None
        signal.signal(signal.SIGINT, lambda *args: self.stop())
        sys.excepthook = lambda et, ev, tb: print("".join(traceback.format_exception(et, ev, tb)))

    def start(self):
        self.detect_device()
        self.media_devices.audioOutputsChanged.connect(self.detect_device)

    def stop(self):
        print("stopping")
        self.socket.close()
        self.source.stateChanged.disconnect()
        self.media_devices.audioOutputsChanged.disconnect()
        self.source.stop()
        self.sink.stop()
        QCoreApplication.quit()

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

def main():
    app = QCoreApplication()
    router = AutoAudioRouter(sys.argv[-1] == "boost")
    router.setup()
    router.start()
    app.exec()

if __name__ == '__main__':
    main()

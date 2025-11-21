import time
from array import array
from PySide6.QtCore import QObject, Signal, QtMsgType, qInstallMessageHandler, QTimer
from PySide6.QtMultimedia import QAudio, QAudioFormat, QAudioSink, QAudioSource, QMediaDevices

class AutoAudioRouter(QObject):
    devices_changed = Signal(dict)

    def __init__(self, boost = False):
        super().__init__()
        self.boost = boost
        self.stopped = False
        self.rebuilding = False
        self.last_rebuild_time = 0
        self.recovery_timer = None
        self.peak_history = [0] * 1000
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
        self.sink.stateChanged.connect(self.state_changed)

    def build_source(self):
        if self.source:
            try:
                self.instream.readyRead.disconnect(self.process_input)
            except (RuntimeError, AttributeError):
                pass
            self.source.stateChanged.disconnect()
            self.source.stop()
        self.source = QAudioSource(self.input_device, self.format, parent=self)
        self.instream = self.source.start()
        self.instream.readyRead.connect(self.process_input)
        self.source.stateChanged.connect(self.state_changed)

    def detect_device(self):
        old_input = self.input_device
        old_fallback = self.fallback_device
        old_primary = self.primary_device

        input_devices, output_devices = self.query_fresh_devices()

        if self.input_device != old_input:
            print("Input device changed:", self.input_device.description())
            self.build_source()

        fallback_changed = self.fallback_device != old_fallback
        primary_changed = self.primary_device != old_primary

        if fallback_changed or primary_changed:
            if self.primary_device:
                if primary_changed:
                    print("Primary device changed:", self.primary_device.description())
                self.build_sink(self.primary_device)
            else:
                if primary_changed:
                    print("Primary device not connected")
                elif fallback_changed:
                    print("Fallback device changed:", self.fallback_device.description())
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

    def state_changed(self, state: QAudio.State):
        if state.value in (QAudio.State.StoppedState.value, QAudio.State.SuspendedState.value) and not self.stopped:
            self.start_recovery_polling()

    def find_device(self, devices, filter):
        return next((d for d in devices if filter in d.description()), None)

    def start_recovery_polling(self):
        if not self.recovery_timer:
            self.recovery_timer = QTimer(self)
            self.recovery_timer.timeout.connect(self.try_recovery)
            self.recovery_timer.start(1000)

    def try_recovery(self):
        source_state = self.source.state() if self.source else None
        sink_state = self.sink.state() if self.sink else None

        stopped_values = (QAudio.State.StoppedState.value, QAudio.State.SuspendedState.value)
        source_needs_rebuild = not self.source or (source_state is not None and source_state.value in stopped_values)
        sink_needs_rebuild = not self.sink or (sink_state is not None and sink_state.value in stopped_values)

        if source_needs_rebuild or sink_needs_rebuild:
            self.query_fresh_devices()
            if source_needs_rebuild:
                self.build_source()
            if sink_needs_rebuild:
                self.build_sink(self.primary_device if self.primary_device else self.fallback_device)
        else:
            self.recovery_timer.stop()
            self.recovery_timer = None

    def query_fresh_devices(self):
        input_devices = self.media_devices.audioInputs()
        output_devices = self.media_devices.audioOutputs()
        self.input_device = self.find_device(input_devices, self.input_filter)
        self.fallback_device = self.find_device(output_devices, self.fallback_filter)
        self.primary_device = self.find_device(output_devices, self.primary_filter)
        return input_devices, output_devices

    def qt_message_handler(self, msg_type, context, message):
        if "Resampling failed" in message:
            self.handle_resampling_error()
        else:
            print(message)

    def handle_resampling_error(self):
        if not self.rebuilding and time.time() - self.last_rebuild_time > 1:
            self.last_rebuild_time = time.time()
            self.rebuilding = True
            self.data = bytes()
            print("Resampling error detected, rebuilding with fresh devices...")
            self.query_fresh_devices()
            self.build_source()
            self.build_sink(self.primary_device if self.primary_device else self.fallback_device)
            self.rebuilding = False

    def run(self):
        qInstallMessageHandler(self.qt_message_handler)
        self.media_devices = QMediaDevices(parent=self)
        self.format = QAudioFormat(parent=self)
        self.format.setSampleRate(48000)
        self.format.setChannelCount(2)
        self.format.setSampleFormat(QAudioFormat.Int16)
        self.detect_device()
        self.media_devices.audioOutputsChanged.connect(self.detect_device)

    def stop(self):
        self.stopped = True
        if self.recovery_timer:
            self.recovery_timer.stop()
        self.source.stop()
        self.sink.stop()

    def process_input(self):
        if self.rebuilding:
            return
        self.outstream.write(self.data)
        self.data = self.instream.read(32000)
        if self.boost:
            samples = array('h', self.data)
            self.peak_history[self.history_index] = max(abs(s) for s in samples)
            self.history_index = (self.history_index + 1) % 1000
            peak_level = max(self.peak_history)
            actual_gain = 32767 / peak_level if peak_level > 10369 else 3.16
            self.data = array('h', (int(s * actual_gain) for s in samples))

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

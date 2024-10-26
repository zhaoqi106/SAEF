from PySide6.QtCore import QThread, Signal
import pyaudio, wave


class AudioRecorder(QThread):
    signal_info = Signal(bytes)

    def __init__(self):
        super().__init__()

        self.m_chunk = 1024
        self.m_format = pyaudio.paInt16
        self.m_channels = 1
        self.m_sr = 48000
        self.m_stop = True
        self.m_path = ""
        self.m_record = False
        self.m_device_index = 0

    def set_params(self, sr):
        self.m_sr = sr

    def set_path(self, path):
        self.m_path = path

    def set_record(self, record):
        self.m_record = record

    def set_device_index(self, index, channels):
        self.m_device_index = index
        self.m_channels = channels

    def run(self):
        p = pyaudio.PyAudio()

        stream = p.open(format=self.m_format,
                        channels=self.m_channels,
                        rate=self.m_sr,
                        input=True,
                        input_device_index=self.m_device_index,
                        frames_per_buffer=self.m_chunk)
        self.m_stop = False
        all_data = b""
        while not self.m_stop:
            data = stream.read(self.m_chunk)
            self.signal_info.emit(data)
            if self.m_record:
                all_data += data
            else:
                if len(all_data) > 0:
                    wf = wave.open(self.m_path + '/audio.wav', 'wb')
                    wf.setnchannels(self.m_channels)
                    wf.setsampwidth(2)
                    wf.setframerate(self.m_sr)
                    wf.writeframes(all_data)
                    wf.close()
                    all_data = b""
        p.terminate()
        self.m_stop = True
        self.m_record = False

    def stop(self):
        self.m_stop = True

    def get_all_devices(self):
        p = pyaudio.PyAudio()
        num = p.get_device_count()
        device_list = []
        for i in range(num):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                device_list.append(info)
        p.terminate()
        return device_list

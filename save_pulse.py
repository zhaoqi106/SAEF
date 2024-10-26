import time
from PySide6.QtCore import QThread
import cv2
import os


class SavePulse(QThread):
    def __init__(self):
        super(SavePulse, self).__init__()
        self.m_stop = True
        self.m_ppg_data = []
        self.m_hr_data = []
        self.m_spo2_data = []
        self.m_save_path = ''

    def init(self):
        self.m_ppg_data.clear()
        self.m_hr_data.clear()
        self.m_spo2_data.clear()
        with open(self.m_save_path + '/heart_rate.txt', 'w') as f:
            f.write('')
        with open(self.m_save_path + '/spo2.txt', 'w') as f:
            f.write('')
        with open(self.m_save_path + '/ppg.txt', 'w') as f:
            f.write('')

    def addHeartRate(self, ts, hr):
        self.m_hr_data.append([ts, hr])

    def addSpo2(self, ts, spo2):
        self.m_spo2_data.append([ts, spo2])

    def addPPG(self, ts, ppg):
        self.m_ppg_data.append([ts, ppg])

    def setParams(self, save_path):
        self.m_save_path = save_path

    def stop(self):
        self.m_stop = True

    def run(self):
        self.init()
        self.m_stop = False
        while not self.m_stop:
            is_work = False
            if len(self.m_hr_data) > 0:
                ts, hr = self.m_hr_data.pop(0)
                with open(self.m_save_path + '/heart_rate.txt', 'a+') as f:
                    f.write('%f %d\n' % (ts, hr))
                is_work = True
            if len(self.m_spo2_data) > 0:
                ts, spo2 = self.m_spo2_data.pop(0)
                with open(self.m_save_path + '/spo2.txt', 'a+') as f:
                    f.write('%f %d\n' % (ts, spo2))
                is_work = True
            if len(self.m_ppg_data) > 0:
                ts, ppg = self.m_ppg_data.pop(0)
                with open(self.m_save_path + '/ppg.txt', 'a+') as f:
                    f.write('%f %d\n' % (ts, ppg[-1]))
                is_work = True

            if not is_work:
                time.sleep(1)


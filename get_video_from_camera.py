import time
from PySide6.QtCore import QThread, Signal
import cv2
# from crypt_module import encrypt
import numpy as np


class GetVideoFromCamera(QThread):
    signal_data = Signal(dict)

    def __init__(self, id):
        super(GetVideoFromCamera, self).__init__()
        self.m_stop = True
        self.m_id = id
        self.m_cam_id = -1
        self.m_video_size = (640, 480)
        self.m_video_size_name = ''
        self.m_trans_format = 'MJPG'
        self.m_cap = None
        self.m_change_params = False
        self.m_first_img = None
        self.m_encrypt = False
        self.m_start_record = False

    def setCamera(self, cam_id, video_size, trans_format, fps):
        if self.m_cam_id != cam_id or self.m_video_size_name != video_size or self.m_trans_format != trans_format or self.m_fps != fps:
            self.m_cam_id = cam_id
            self.m_trans_format = trans_format
            self.m_fps = fps
            self.m_video_size_name = video_size
            if video_size == '480p':
                self.m_video_size = (640, 480)
            elif video_size == '720p':
                self.m_video_size = (1280, 720)
            else:
                self.m_video_size = (1920, 1080)

            self.m_change_params = True


    def setEncrypt(self, encrypt):
        self.m_encrypt = encrypt

    def setStartRecord(self, is_start):
        self.m_start_record = is_start
        self.m_first_img = None

    def changeCamera(self):
        while not self.m_stop:
            try:
                self.signal_data.emit(
                    {'id': self.m_id, 'ret': -1, 'msg': f'Camera {self.m_id} is connecting'})
                if self.m_cap:
                    self.m_cap.release()
                while self.m_cam_id < 0:
                    time.sleep(1)
                self.m_cap = cv2.VideoCapture(self.m_cam_id)
                # set camera params
                self.m_cap.set(5, self.m_fps)
                self.m_cap.set(3, self.m_video_size[0])
                self.m_cap.set(4, self.m_video_size[1])
                self.m_cap.set(6, cv2.VideoWriter.fourcc(*self.m_trans_format))
                ret, _ = self.m_cap.read()
                if ret:
                    self.m_change_params = False
                    self.signal_data.emit(
                        {'id': self.m_id, 'ret': -2, 'msg': f'Camera {self.m_id} is connecting'})
                    break
                else:
                    self.signal_data.emit(
                        {'id': self.m_id, 'ret': -3, 'msg': f'Camera {self.m_id} open failed, try open again...'})
                    time.sleep(1)
            except:
                self.m_cap = None
                self.signal_data.emit({'id': self.m_id, 'ret': -3, 'msg': f'Camera {self.m_id} open failed, try open again...'})
                time.sleep(1)



    def stop(self):
        self.m_stop = True

    def run(self):
        print("start open camera")
        self.m_stop = False
        self.changeCamera()
        f = open("temp.txt", 'w')
        while not self.m_stop and self.m_cap is not None:
            ret, frame = self.m_cap.read()
            ts = time.time()
            if ret:
                self.signal_data.emit({
                    'id': self.m_id, 'ret': 0, 'msg': '', 'data': frame, 'ts': ts,
                    'start_record': self.m_start_record, 'key': self.m_first_img
                })
                f.write("%f\n" % ts)
            else:
                self.signal_data.emit(
                    {'id': self.m_id, 'ret': -3, 'msg': f'Camera {self.m_id} open failed, try open again...'})
                time.sleep(1)
            if self.m_change_params:
                self.changeCamera()
        self.m_stop = True
        if self.m_cap is not None:
            self.m_cap.release()
        print(f"camera {self.m_id} is stop!")
        self.signal_data.emit({'id': self.m_id, 'ret': -3, 'msg': f'Camera {self.m_id} stop!'})


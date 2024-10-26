import os
import cv2
import numpy as np
from face_detect.face_detect import FaceDetect
from PySide6 import QtWidgets
import pyqtgraph as pg
from PyCameraList.camera_device import list_video_devices
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QMessageBox, QFileDialog
from face_detect.face_detect import FaceDetect
from UI.DemoUI import Ui_Form
from get_video_from_camera import GetVideoFromCamera
import time
from rppg_alg.predict import RppgAlg


def getEuclideanDistance(x1, y1, x2, y2):
    return np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

def getCenterBox(boxes, kpes, width, height):
    best_box = []
    best_kp = []
    best_distance = width * height
    center_x = width / 2
    center_y = height / 2
    for i, box in enumerate(boxes):
        x1, y1, x2, y2 = box
        distance = getEuclideanDistance((x1 + x2) / 2, (y1 + y2) / 2, center_x, center_y)
        if distance < best_distance:
            best_distance = distance
            best_box = box
            best_kp = kpes[i]
    return best_box, best_kp

class GetFaceLoc(QThread):
    signal_data = Signal(dict)

    def __init__(self):
        super().__init__()
        self.m_stop = True
        self.m_fd = FaceDetect(test_device='cpu')
        self.m_image_list = []
        self.m_face_list = []

        self.m_img_size = 36

    def set_params(self, ts, image):
        self.m_image_list.append([ts, image])

    def run(self):
        try:
            self.m_stop = False
            prev_box = None
            box_size = None
            face_list = []
            ts_list = []
            while not self.m_stop:
                if len(self.m_image_list) > 0:
                    ts, frame = self.m_image_list.pop(0)
                    height, width = frame.shape[:2]
                    boxes, kpes = self.m_fd.getFaceLoc(frame)
                    if len(boxes) > 1:
                        box, kp = getCenterBox(boxes, kpes, width, height)
                    elif len(boxes) == 0:
                        continue
                    else:
                        box = boxes[0]

                    if prev_box is not None:
                        box = np.array(box) * 0.1 + prev_box * 0.9
                        prev_box = box
                    x1, y1, x2, y2 = box
                    minx = np.min((x1, x2))
                    maxx = np.max((x1, x2))
                    miny = np.min((y1, y2))
                    maxy = np.max((y1, y2))
                    cnt_x = np.round((minx + maxx) / 2).astype('int')
                    cnt_y = np.round((maxy + miny) / 2).astype('int')

                    curr_box_size = np.round(1. * (maxy - miny)).astype('int')
                    if box_size is not None:
                        box_size = int(curr_box_size * 0.1 + box_size * 0.9)
                    else:
                        box_size = curr_box_size

                    box_half_size = int(box_size / 2)
                    face = frame[max([cnt_y - box_half_size, 0]): cnt_y - box_half_size + box_size,
                           max([cnt_x - box_half_size, 0]): cnt_x - box_half_size + box_size]
                    face = cv2.resize(face, (self.m_img_size, self.m_img_size), cv2.INTER_AREA)
                    face_list.append(face)
                    ts_list.append(ts)
                    if len(face_list) == 257:
                        self.signal_data.emit({
                            'ret': 1, 'face_list': face_list[:], 'ts_list': ts_list[:]
                        })
                        face_list.clear()
                        ts_list.clear()
                        self.m_image_list.clear()


            self.signal_data.emit({'ret': 2, 'msg': 'finish'})
        except Exception as e:
            self.signal_data.emit({'ret': -1, 'msg': str(e)})

    def stop(self):
        self.m_stop = True


class Demo(QtWidgets.QWidget, Ui_Form):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.setWindowTitle("rPPGDemo V2.0.0")

        self.btn_stop.clicked.connect(self.stop)
        self.btn_start.clicked.connect(self.start)
        self.btn_stop.setEnabled(False)

        pg.setConfigOption('background', '#000000')
        ppg_graph = pg.GraphicsLayoutWidget()
        self.vl_ppg.addWidget(ppg_graph)
        self.m_ppg_view = ppg_graph.addPlot()
        self.m_ppg_view.hideAxis('left')
        self.m_ppg_view.hideAxis('bottom')
        # self.m_ppg_view.setYRange(0, 100)
        self.m_ppg_plot = self.m_ppg_view.plot([], [], pen=pg.mkPen('r', width=4))

        self.m_log_info_list = []

        # video fps
        self.m_fps = 30

        self.m_alg_start = False

        # get all cameras on current PC
        self.m_camera_info = {}
        for cam in list_video_devices():
            self.m_camera_info[cam[1]] = cam[0]
        self.m_camera_num = len(self.m_camera_info.keys())
        self.m_camera_list = [{'camera_list': self.cb_camera_list,
                               'status': self.label_cam_sta,
                               'get_video': GetVideoFromCamera(0),
                               'face_loc_alg': GetFaceLoc(),
                               'rppg_alg': RppgAlg(),
                               'show_label': self.label_video}]
        for i, name in enumerate(self.m_camera_info):
            self.m_camera_list[i]['camera_list'].addItems(self.m_camera_info.keys())
            self.m_camera_list[i]['camera_list'].setCurrentIndex(i)
            self.m_camera_list[i]['camera_list'].currentIndexChanged.connect(self.updateVideoParams)
            self.m_camera_list[i]['camera_list'].setEnabled(True)
            self.m_camera_list[i]['status'].setText("connecting")
            self.m_camera_list[i]['get_video'].signal_data.connect(self.recvFrameData)
            self.m_camera_list[i]['get_video'].start()
            self.m_camera_list[i]['face_loc_alg'].signal_data.connect(self.recvFaceList)
            self.m_camera_list[i]['rppg_alg'].signal_data.connect(self.recvPPG)

        # available video size
        self.cb_size.addItems(['480p', '720p', '1080p'])

        # available trans format
        self.cb_trans_format.addItems(['MJPG', 'YUY2'])
        self.cb_trans_format.setCurrentIndex(1)

        self.updateVideoParams()
        for i in range(len(self.m_camera_info)):
            self.m_camera_list[i]['get_video'].start()

    def start(self):
        self.m_alg_start = True
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        for i in range(len(self.m_camera_list)):
            self.m_camera_list[i]['face_loc_alg'].start()
            self.m_camera_list[i]['rppg_alg'].start()

    def stop(self):
        self.m_alg_start = False
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

        for i in range(len(self.m_camera_list)):
            self.m_camera_list[i]['face_loc_alg'].stop()
            self.m_camera_list[i]['rppg_alg'].stop()

    def addLogInfo(self, msg):
        if len(self.m_log_info_list) == 0 or self.m_log_info_list[-1][1] != msg:
            time_str = time.strftime("%H:%M:%S", time.localtime())
            self.m_log_info_list.append([time_str, msg])
        if len(self.m_log_info_list) > 0:
            info = '\n'.join([val[0] + '  ' + val[1] for val in self.m_log_info_list])
            self.textBrowser.setText(info)

    def recvFrameData(self, data):
        idx = data['id']
        if data['ret'] < 0:
            if data['ret'] == -1:
                self.m_camera_list[idx]['status'].setText("connecting")
                self.m_camera_list[idx]['status'].setStyleSheet("color: Blue")
            elif data['ret'] == -2:
                self.m_camera_list[idx]['status'].setText("connected")
                self.m_camera_list[idx]['status'].setStyleSheet("color: Green")
            elif data['ret'] == -3:
                self.m_camera_list[idx]['status'].setText("disconnected")
                self.m_camera_list[idx]['status'].setStyleSheet("color: Red")
                # read error
                self.addLogInfo(data['msg'])
        else:
            frame = data['data']
            ts = data['ts']
            if self.m_alg_start:
                self.m_camera_list[idx]['face_loc_alg'].set_params(ts, frame)

            # show video
            h = 720 // 4
            w = 1280 // 4
            frame = cv2.resize(frame, (w, h), interpolation=cv2.INTER_AREA)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            a = QImage(frame.data, frame.shape[1], frame.shape[0], QImage.Format_RGB888)
            self.m_camera_list[idx]['show_label'].setPixmap(QPixmap.fromImage(a))
            self.m_camera_list[idx]['show_label'].setScaledContents(True)

    def recvFaceList(self, data):
        ret = data['ret']
        if ret == 1:
            face_list = data['face_list']
            ts_list = data['ts_list']
            self.m_camera_list[0]['rppg_alg'].set_data(ts_list, face_list)

    def recvPPG(self, data):
        ret = data['ret']
        if ret == 0:
            hr = data['hr']
            signal = data['signal']
            self.label_hr.setText("%.1f BPM" % hr)
            self.m_ppg_plot.setData(signal)

    def updateVideoParams(self):
        '''
        update video params, including camera, video size and trans-format
        '''
        try:
            # ---------------------------------------------------------------------#
            #   check camera
            # ---------------------------------------------------------------------#
            camera_list = []
            for i in range(self.m_camera_num):
                cam_id = self.m_camera_list[i]['camera_list'].currentText()
                if cam_id in camera_list:
                    QMessageBox.warning(self, 'Warning', "You cannot open two identical cameras at the same time!", QMessageBox.Close)
                    return
                camera_list.append(cam_id)

            video_size = self.cb_size.currentText()
            trans_format = self.cb_trans_format.currentText()
            for i in range(self.m_camera_num):
                cam_id = self.m_camera_list[i]['camera_list'].currentText()
                cam_id = self.m_camera_info[cam_id]
                self.m_camera_list[i]['get_video'].setCamera(cam_id, video_size, trans_format, self.m_fps)
        except:
            self.addLogInfo("Camera setting failed!")
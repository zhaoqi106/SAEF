import os
import cv2
import numpy as np
from face_detect.face_detect import FaceDetect
from PySide6 import QtWidgets
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QMessageBox, QFileDialog
from UI.PostUI import Ui_Form
import time
from crypt_module_adv import encrypt_image


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


class ReadAndPost(QThread):
    signal_data = Signal(dict)

    def __init__(self):
        super().__init__()
        self.m_stop = True
        self.m_fd = FaceDetect(test_device='cpu')
        self.m_ori_file = None
        self.m_dst_file = None
        self.m_mask_eye = False
        self.m_mask_mouth = False
        self.m_encrypt = 'None'
        self.m_key = None

    def set_params(self, ori_file, dst_file, mask_eye=False, mask_mouth=False, encrypt='AES', key=None):
        self.m_ori_file = ori_file
        self.m_dst_file = dst_file
        self.m_mask_eye = mask_eye
        self.m_mask_mouth = mask_mouth
        self.m_encrypt = encrypt
        self.m_key = key

    def run(self):
        try:
            cap = cv2.VideoCapture(self.m_ori_file)
            filename = os.path.split(self.m_ori_file)[1]
            _format = self.m_ori_file.split('.')[-2].split('_')[-1]
            if _format not in ['MJPG', 'FFV1']:
                _format = 'FFV1'
            fourcc = cv2.VideoWriter_fourcc(*_format)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            curr_cnt = 0
            out = cv2.VideoWriter(self.m_dst_file + '/mask_' + filename, fourcc, fps, (width, height), True)
            self.m_stop = False
            last_kp = None
            mask = None
            while not self.m_stop:
                ret, frame = cap.read()
                if not ret:
                    break
                boxes, kpes = self.m_fd.getFaceLoc(frame)
                if len(boxes) > 1:
                    box, kp = getCenterBox(boxes, kpes, width, height)
                elif len(boxes) == 0:
                    kp = last_kp
                else:
                    box = boxes[0]
                    kp = kpes[0]
                # if last_kp is not None:
                #     kp = 0.1 * kp + 0.9 * last_kp
                frame_mask = self.mask_alg(frame, kp_box=kp)

                if self.m_encrypt > 0:
                    frame_mask = encrypt_image(frame_mask, self.m_encrypt, self.m_key, mask)
                    if self.m_encrypt == 1 and mask is None:
                        mask = frame_mask

                last_kp = kp
                out.write(frame_mask)
                curr_cnt += 1
                self.signal_data.emit({
                    'ret': 1, 'frame': frame, 'mask': frame_mask, 'progress': int(100 * curr_cnt // total_frames)
                })
            self.signal_data.emit({'ret': 2, 'msg': 'finish'})
            out.release()
        except Exception as e:
            self.signal_data.emit({'ret': -1, 'msg': str(e)})

    def stop(self):
        self.m_stop = True

    def mask_alg(self, frame, kp_box):
        if kp_box is None:
            return frame
        if self.m_mask_eye:
            mask = np.zeros_like(frame, dtype=np.uint8)
            cv2.line(mask, (kp_box[0], kp_box[1]), (kp_box[2], kp_box[3]), (255, 255, 255), 1)
            k = max(abs(kp_box[2] - kp_box[0]), abs(kp_box[3] - kp_box[1]))
            kernel = np.ones((k // 2, k), np.uint8)
            mask = cv2.dilate(mask, kernel, 1)
            frame = cv2.subtract(frame, mask)
        if self.m_mask_mouth:
            mask = np.zeros_like(frame, dtype=np.uint8)
            cv2.line(mask, (kp_box[6], kp_box[7]), (kp_box[8], kp_box[9]), (255, 255, 255), 1)
            k = max(abs(kp_box[8] - kp_box[6]), abs(kp_box[9] - kp_box[7]))
            kernel = np.ones((k // 2, 1), np.uint8)
            mask = cv2.dilate(mask, kernel, 1)
            frame = cv2.subtract(frame, mask)




        return frame


class PostAlg(QtWidgets.QWidget, Ui_Form):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.setWindowTitle("rPPGCollectTool V2.0.0")

        self.btn_open_keyfile.clicked.connect(self.openKeyFile)
        self.btn_stop.clicked.connect(self.stop)
        self.btn_start.clicked.connect(self.start)
        self.btn_open_file_path.clicked.connect(self.openFilePath)
        self.btn_open_save_path.clicked.connect(self.openSavePath)

        self.cb_encryption.clear()
        self.cb_encryption.addItems(['None', 'XOR', 'Tea', 'AES', 'DES'])

        self.progressBar.setValue(0)

        self.m_read_and_post = ReadAndPost()
        self.m_read_and_post.signal_data.connect(self.getFrames)

    def openKeyFile(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open Key File", os.getcwd())
        if len(filename) > 0:
            self.le_keyfile.setText(filename)

    def stop(self):
        self.m_read_and_post.stop()
        self.set_ui_state(True)

    def start(self):
        file_path = self.le_file_path.text().strip()
        if len(file_path) == 0:
            QMessageBox.warning(self, "warning", "File Path cannot empty!")
            return
        save_path = self.le_save_path.text().strip()
        if len(save_path) == 0:
            QMessageBox.warning(self, "warning", "Save Path cannot empty!")
            return

        encrypt = self.cb_encryption.currentIndex()
        keyfile = self.le_keyfile.text().strip()
        if encrypt > 0 and len(keyfile) == 0:
            QMessageBox.warning(self, "warning", "Key file cannot empty!")
            return
        try:
            with open(keyfile, 'r') as f:
                key = f.readlines()
            key = key[0].strip().split(',')
            key = [eval(val) for val in key]
        except:
            QMessageBox.warning(self, "warning", "Key file load failed!")
            return


        mask_eye = self.cb_eye.isChecked()
        mask_mouth = self.cb_mouth.isChecked()
        self.m_read_and_post.set_params(file_path, save_path, mask_eye, mask_mouth, encrypt=encrypt, key=key)
        self.m_read_and_post.start()
        self.set_ui_state(False)

    def openFilePath(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open Video File", os.getcwd(), "MP4 (*.mp4);AVI (*.avi)")
        if len(filename) > 0:
            self.le_file_path.setText(filename)

    def openSavePath(self):
        save_path = QFileDialog.getExistingDirectory(self, "Open Save Path", os.getcwd())
        if len(save_path) > 0:
            self.le_save_path.setText(save_path)

    def getFrames(self, info):
        ret = info['ret']
        if ret == 1:
            frame = info['frame']
            mask = info['mask']
            progress = info['progress']
            h = 720 // 4
            w = 1280 // 4
            frame = cv2.resize(frame, (w, h), interpolation=cv2.INTER_AREA)
            mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_AREA)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2RGB)
            a = QImage(frame.data, frame.shape[1], frame.shape[0], QImage.Format_RGB888)
            self.label_image_1.setPixmap(QPixmap.fromImage(a))
            self.label_image_1.setScaledContents(True)
            a = QImage(mask.data, mask.shape[1], mask.shape[0], QImage.Format_RGB888)
            self.label_image_2.setPixmap(QPixmap.fromImage(a))
            self.label_image_2.setScaledContents(True)
            self.progressBar.setValue(progress)
        else:
            msg = info['msg']
            self.add_info(msg)
            self.stop()

    def set_ui_state(self, state):
        self.btn_start.setEnabled(state)
        self.btn_open_keyfile.setEnabled(state)
        self.btn_open_save_path.setEnabled(state)
        self.btn_open_file_path.setEnabled(state)
        self.cb_eye.setEnabled(state)
        self.cb_mouth.setEnabled(state)
        self.cb_encryption.setEnabled(state)

        self.btn_stop.setEnabled(not state)

    def add_info(self, msg):
        self.textBrowser.append(msg)
        # self.textBrowser.moveCursor(self.textBrowser.textCursor().End)
        time.sleep(0.1)


if __name__ == '__main__':
    import sys

    app = QtWidgets.QApplication(sys.argv)
    demo = PostAlg()
    demo.show()
    sys.exit(app.exec_())


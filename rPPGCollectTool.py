import os.path
from PySide6.QtCore import Qt
from PySide6 import QtWidgets
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import QThread, Signal, QTimer
from PySide6.QtWidgets import QMessageBox, QFileDialog
from PyCameraList.camera_device import list_video_devices
import pyqtgraph as pg
import numpy as np
import shutil
import cv2
import time
from UI.MainUI import Ui_Form
from get_data_from_CMS50E import GetDataFromCMS50E
from get_video_from_camera import GetVideoFromCamera
from save_video import SaveVideo
from save_pulse import SavePulse
from AudioRecorder import AudioRecorder


class MyDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Window | Qt.FramelessWindowHint)
        self.setWindowTitle("处理中")
        self.m_parent = parent
        self.m_layout = QtWidgets.QVBoxLayout(self)
        self.m_label = QtWidgets.QLabel("正在进行后处理，请耐心等待...")
        self.m_layout.addWidget(self.m_label)

        self.m_timer = QTimer()
        self.m_timer.timeout.connect(self.check)
        self.m_timer.start(1000)

    def check(self):
        num = 0
        for i in range(len(self.m_parent.m_camera_list)):
            if self.m_parent.m_camera_list[i]['save_video'].m_final_stop:
                num += 1
        if num == len(self.m_parent.m_camera_list):
            self.close()

class MyTimer(QThread):
    signal_data = Signal(int)

    def __init__(self, gap):
        super(MyTimer, self).__init__()
        self.m_stop = True
        self.m_gap = gap

    def run(self):
        self.m_stop = False
        while not self.m_stop:
            self.signal_data.emit(0)
            time.sleep(self.m_gap)

    def stop(self):
        self.m_stop = True


class rPPGCollectTool(QtWidgets.QWidget, Ui_Form):
    def __init__(self):
        super(rPPGCollectTool, self).__init__()
        self.setupUi(self)

        self.setWindowTitle("rPPGCollectTool V2.1.1")

        # button connection
        self.btn_start.clicked.connect(self.start)
        self.btn_stop.clicked.connect(self.stop)
        self.btn_stop.setEnabled(False)

        # self.cb_scenario_info.clear()
        # self.cb_scenario_info.addItems(['JX', 'CS', 'JQ', 'ZQ'])

        # set ppg graph
        # pg.setConfigOption('background', '#F0F0F0')
        pg.setConfigOption('background', '#000000')
        ppg_graph = pg.GraphicsLayoutWidget()
        self.vl_ppg.addWidget(ppg_graph)
        self.m_ppg_view = ppg_graph.addPlot()
        self.m_ppg_view.hideAxis('left')
        self.m_ppg_view.hideAxis('bottom')
        self.m_ppg_view.setYRange(0, 100)
        self.m_left_ppg_plot = self.m_ppg_view.plot([], [], pen=pg.mkPen('r', width=4))
        self.m_right_ppg_plot = self.m_ppg_view.plot([], [], pen=pg.mkPen('r', width=4))
        # 音频相关画图
        pg.setConfigOption('background', '#f3f3f3')
        audio_graph = pg.GraphicsLayoutWidget()
        self.vl_audio.addWidget(audio_graph)
        self.m_audio_view = audio_graph.addPlot()
        self.m_audio_view.hideAxis('left')
        self.m_audio_view.hideAxis('bottom')
        self.m_audio_view.setYRange(-5000, 5000)
        self.m_audio_plot = self.m_audio_view.plot([], pen=pg.mkPen('b', width=2))
        # self.m_audio_cache_data = []

        # ppg data cache
        self.m_ppg_max_num = 255
        self.m_ppg_x = np.linspace(0, self.m_ppg_max_num, self.m_ppg_max_num)
        self.m_ppg_signal = [64] * self.m_ppg_max_num
        self.m_curr_ppg_index = 0

        # get all cameras on current PC
        self.m_camera_info = {}
        for cam in list_video_devices():
            num = 0
            name = cam[1]
            while name in self.m_camera_info:
                num += 1
                name = cam[1] + '-%d' % num
            self.m_camera_info[name] = cam[0]
        self.m_camera_num = len(self.m_camera_info.keys())

        # camera list: {'camera_list': all cameras,
        #               'status': connected or not,
        #               'get_video': thread of get frames of each camera,
        #               'save_video': thread for save video of each camera,
        #               'show_label': label for show on ui of each camera}
        self.m_camera_list = [
            {'camera_list': self.cb_camera_list_1, 'status': self.label_cam_sta_1, 'get_video': GetVideoFromCamera(0),
             'save_video': SaveVideo(), 'show_label': self.label_video_1},
            {'camera_list': self.cb_camera_list_2, 'status': self.label_cam_sta_2, 'get_video': GetVideoFromCamera(1),
             'save_video': SaveVideo(), 'show_label': self.label_video_2},
            {'camera_list': self.cb_camera_list_3, 'status': self.label_cam_sta_3, 'get_video': GetVideoFromCamera(2),
             'save_video': SaveVideo(), 'show_label': self.label_video_3},
            {'camera_list': self.cb_camera_list_4, 'status': self.label_cam_sta_4, 'get_video': GetVideoFromCamera(3),
             'save_video': SaveVideo(), 'show_label': self.label_video_4},
        ]
        for i in range(len(self.m_camera_list)):
            self.m_camera_list[i]['camera_list'].addItems(self.m_camera_info.keys())
            self.m_camera_list[i]['camera_list'].setCurrentIndex(i)
            self.m_camera_list[i]['camera_list'].currentIndexChanged.connect(self.updateVideoParams)
            self.m_camera_list[i]['camera_list'].setEnabled(True)
            self.m_camera_list[i]['status'].setText("connecting")
            self.m_camera_list[i]['get_video'].signal_data.connect(self.recvFrameData)

        # available video size
        self.cb_size.addItems(['480p', '720p', '1080p'])
        self.cb_size.setCurrentIndex(2)

        # available trans format
        self.cb_trans_format.addItems(['MJPG', 'YUY2'])
        self.cb_trans_format.setCurrentIndex(0)
        self.cb_mjpg.setChecked(True)
        self.cb_ffv1.setChecked(False)
        self.cb_pngs.setChecked(True)

        self.le_duration.setText("180")

        # video fps
        self.m_fps = 30

        # sub threading
        # threading of getting PPG from CMS50E device
        self.m_ppg_receiver = GetDataFromCMS50E()
        self.m_ppg_receiver.signal_data.connect(self.recvPPGData)
        # threading of update the ppg waveforms
        self.m_update_graph_timer = MyTimer(0.1)
        self.m_update_graph_timer.signal_data.connect(self.updateGraph)
        # threading of saving video and ppg data
        self.m_pulse_saver = SavePulse()

        # start recoding or not and start timestamp and recoding duration
        self.m_save_data = False
        self.m_start_ts = -1
        self.m_duration = -1

        # real-time updating while the parameters changed
        self.cb_size.currentIndexChanged.connect(self.updateVideoParams)
        self.cb_trans_format.currentIndexChanged.connect(self.updateVideoParams)

        self.le_person_abbre.textChanged.connect(self.updateDataCode)
        self.cb_scenario_info.currentIndexChanged.connect(self.updateDataCode)

        # set save path, if save path not exists, make it
        self.m_save_path = 'save_data'
        if not os.path.exists(self.m_save_path):
            os.mkdir(self.m_save_path)

        self.m_log_info_list = []

        self.updateVideoParams()
        # update video params and start opening camera and reading ppg data while this app stated.
        self.m_ppg_receiver.start()
        self.m_update_graph_timer.start()
        for i in range(len(self.m_camera_list)):
            self.m_camera_list[i]['get_video'].start()

        self.m_audio_recorder = AudioRecorder()
        self.m_audio_recorder.signal_info.connect(self.recv_audio_data)
        self.m_audio_device_list = self.m_audio_recorder.get_all_devices()
        for i in range(len(self.m_audio_device_list)):
            self.cb_mic_list.addItem(self.m_audio_device_list[i]['name'])
        self.btn_mic_start.clicked.connect(self.start_mic)
        self.cb_use_mic.checkStateChanged.connect(self.use_mic_change)

        self.m_info_dialog = MyDialog(self)

    def use_mic_change(self):
        if self.cb_use_mic.isChecked():
            self.cb_mic_list.setEnabled(True)
            self.btn_mic_start.setEnabled(True)
        else:
            self.cb_mic_list.setEnabled(False)
            self.btn_mic_start.setEnabled(False)
            self.btn_mic_start.setText("开启")
            self.m_audio_recorder.stop()

    def start_mic(self):
        if self.btn_mic_start.text() == '开启':
            self.btn_mic_start.setText("关闭")
            self.m_audio_recorder.set_params(48000)
            idx = self.cb_mic_list.currentIndex()
            idx = self.m_audio_device_list[idx]['index']
            chs = self.m_audio_device_list[idx]['maxInputChannels']
            self.m_audio_recorder.set_device_index(idx, chs)
            self.m_audio_recorder.start()
        else:
            self.btn_mic_start.setText("开启")
            self.m_audio_recorder.stop()

    def recv_audio_data(self, data):
        data = np.frombuffer(data, dtype=np.int16)
        win = np.hanning(len(data))
        data = data * win
        self.m_audio_plot.setData(data)

    def updateDataCode(self):
        person_abbre = self.le_person_abbre.text().strip()
        if len(person_abbre) > 0:
            scenario_info = self.cb_scenario_info.currentText()
            save_path = self.m_save_path + '/' + person_abbre + '/' + scenario_info + '/'
            if os.path.exists(save_path):
                folder_list = os.listdir(save_path)
                max_val = 1
                for folder in folder_list:
                    try:
                        val = int(folder)
                        if val >= max_val:
                            max_val = val + 1
                    except:
                        continue
                max_val = "%03d" % max_val
                self.le_data_code.setText(max_val)
            else:
                self.le_data_code.setText("001")

    def updateVideoParams(self):
        '''
        update video params, including camera, video size and trans-format
        '''
        try:
            # ---------------------------------------------------------------------#
            #   check camera
            # ---------------------------------------------------------------------#
            camera_list = []
            for i in range(len(self.m_camera_list)):
                cam_id = self.m_camera_list[i]['camera_list'].currentText()
                if len(cam_id) == 0:
                    continue
                if cam_id in camera_list:
                    QMessageBox.warning(self, 'Warning', "You cannot open two identical cameras at the same time!", QMessageBox.Close)
                    return
                camera_list.append(cam_id)

            video_size = self.cb_size.currentText()
            trans_format = self.cb_trans_format.currentText()
            for i in range(len(self.m_camera_list)):
                cam_id = self.m_camera_list[i]['camera_list'].currentText()
                if len(cam_id) > 0 and cam_id in self.m_camera_info:
                    cam_id = self.m_camera_info[cam_id]
                else:
                    cam_id = -1
                self.m_camera_list[i]['get_video'].setCamera(cam_id, video_size, trans_format, self.m_fps)
        except:
            self.addLogInfo("Camera setting failed!")

    def start(self):
        '''
        start recoding video and ppg info
        '''
        self.m_log_info_list.clear()
        self.textBrowser.clear()
        try:
            person_abbre = self.le_person_abbre.text().strip()
            scenario_info = self.cb_scenario_info.currentText()
            data_code = self.le_data_code.text().strip()
        except:
            QMessageBox.warning(self, 'Warning', "Text error!", QMessageBox.Close)
            return
        try:
            self.m_duration = int(self.le_duration.text().strip())
        except:
            QMessageBox.warning(self, 'Warning', "duration must be integer!", QMessageBox.Close)
            return

        save_format_list = []
        if self.cb_mjpg.isChecked():
            save_format_list.append('MJPG')
        if self.cb_pngs.isChecked():
            save_format_list.append('PNG')
        if self.cb_ffv1.isChecked():
            save_format_list.append('FFV1')


        _save_path = self.m_save_path + '/' + person_abbre + '/' + scenario_info + '/' + data_code
        # check save path
        if os.path.exists(_save_path):
            reply = QMessageBox.warning(self, "Warning", f"The path of 'f{_save_path}' already exists!\n "
                                                         f"would you want to replace it?",
                                        QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                shutil.rmtree(_save_path)
                os.mkdir(_save_path)
            else:
                return

        save_path = self.m_save_path + '/' + person_abbre + '/'
        if not os.path.exists(save_path):
            os.mkdir(save_path)
        save_path += scenario_info + '/'
        if not os.path.exists(save_path):
            os.mkdir(save_path)
        save_path += data_code + '/'
        if not os.path.exists(save_path):
            os.mkdir(save_path)

        self.m_pulse_saver.setParams(save_path)
        self.m_pulse_saver.start()

        for i in range(len(self.m_camera_list)):
            if self.m_camera_list[i]['camera_list'].currentText():
                self.m_camera_list[i]['get_video'].setStartRecord(True)
                self.m_camera_list[i]['save_video'].setParams(save_path, save_format_list, self.m_fps,
                                                              self.m_camera_list[i]['get_video'].m_video_size[1],
                                                              self.m_camera_list[i]['get_video'].m_video_size[0],
                                                              self.m_camera_list[i]['camera_list'].currentText())
                self.m_camera_list[i]['save_video'].start()
        self.m_audio_recorder.set_path(save_path)

        self.btn_stop.setEnabled(True)
        self.btn_start.setEnabled(False)
        self.m_save_data = True
        self.setViewState(False)
        self.addLogInfo("Start recording！")
        self.saveInfo(save_path)

    def saveInfo(self, save_path):
        try:
            with open(save_path + '/info.txt', 'w') as f:
                f.write(f'Camera model:\n')
                for i in range(len(self.m_camera_list)):
                    cam_name = self.m_camera_list[i]['camera_list'].currentText()
                    f.write(f'\t{cam_name}\n')

                codec = self.cb_trans_format.currentText()
                f.write(f'Camera codec: {codec}\n')
                size = self.cb_size.currentText()
                f.write(f'Size: {size}\n')
                m = round(time.time())
                n = time.localtime(m)
                k = time.strftime("%Y-%m-%d %H:%M:%S", n)
                f.write(f'Date: {k}')
        except:
            self.addLogInfo("save info error!")

    def setViewState(self, state):
        self.cb_size.setEnabled(state)
        self.cb_trans_format.setEnabled(state)
        self.cb_camera_list_1.setEnabled(state)
        self.cb_camera_list_2.setEnabled(state)
        self.cb_camera_list_3.setEnabled(state)
        self.cb_camera_list_4.setEnabled(state)
        self.cb_mjpg.setEnabled(state)
        self.cb_pngs.setEnabled(state)
        self.cb_ffv1.setEnabled(state)
        self.le_duration.setEnabled(state)
        self.le_data_code.setEnabled(state)
        self.le_person_abbre.setEnabled(state)
        self.cb_scenario_info.setEnabled(state)

    def stop(self):
        for i in range(len(self.m_camera_list)):
            self.m_camera_list[i]['get_video'].setStartRecord(False)
            self.m_camera_list[i]['save_video'].stop()
        self.m_pulse_saver.stop()
        self.m_audio_recorder.set_record(False)
        self.btn_stop.setEnabled(False)
        self.btn_start.setEnabled(True)
        self.m_save_data = False
        self.m_start_ts = -1
        self.m_duration = -1
        self.setViewState(True)
        self.addLogInfo("Stop recording!")
        self.updateDataCode()

        self.m_info_dialog.exec()

        QMessageBox.information(self, "Information", "Record is finished!")

    def updateGraph(self):
        try:
            self.m_left_ppg_plot.setData(self.m_ppg_x[:self.m_curr_ppg_index], self.m_ppg_signal[:self.m_curr_ppg_index])
            self.m_right_ppg_plot.setData(self.m_ppg_x[self.m_curr_ppg_index + 1:],
                                        self.m_ppg_signal[self.m_curr_ppg_index + 1:])
        except:
            self.addLogInfo("updateGraph error!")

    def addLogInfo(self, msg):
        if len(self.m_log_info_list) == 0 or self.m_log_info_list[-1][1] != msg:
            time_str = time.strftime("%H:%M:%S", time.localtime())
            self.m_log_info_list.append([time_str, msg])
        if len(self.m_log_info_list) > 0:
            info = '\n'.join([val[0] + '  ' + val[1] for val in self.m_log_info_list])
            self.textBrowser.setText(info)

    def recvPPGData(self, data):
        if data['ret'] < 0:
            self.addLogInfo(data['msg'])
        else:
            ts = data['ts']
            if 'hr' in data and len(data['hr']) > 0:
                hr = data['hr'][-1]
                self.label_hr.setText("%d BPM" % hr)
                if self.m_save_data:
                    self.m_pulse_saver.addHeartRate(ts, hr)
            if 'spo2' in data and len(data['spo2']) > 0:
                spo2 = data['spo2'][-1]
                self.label_spo2.setText("%d %%" % spo2)
                if self.m_save_data:
                    self.m_pulse_saver.addSpo2(ts, spo2)
            if 'ppg' in data and len(data['ppg']) > 0:
                num = len(data['ppg'])
                for i in range(num):
                    self.m_ppg_signal[self.m_curr_ppg_index] = data['ppg'][i]
                    self.m_curr_ppg_index += 1
                    if self.m_curr_ppg_index == self.m_ppg_max_num:
                        self.m_curr_ppg_index = 0
                if self.m_save_data:
                    if num > 0:
                        self.m_pulse_saver.addPPG(ts, data['ppg'])

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
            # en_frame = data['en_data']
            ts = data['ts']
            start_record = data['start_record']
            key = data['key']
            if start_record:
                if not self.m_audio_recorder.m_record:
                    self.m_audio_recorder.set_record(True)
                self.m_camera_list[idx]['save_video'].addFrame(ts, frame)

            # show video
            h = 720 // 4
            w = 1280 // 4
            frame = cv2.resize(frame, (w, h), interpolation=cv2.INTER_NEAREST)
            if self.m_save_data:
                if self.m_start_ts < 0:
                    self.m_start_ts = ts
                cv2.putText(frame, f'{ts - self.m_start_ts:.2f}s', (30, 30), cv2.FONT_HERSHEY_COMPLEX,
                            1.0, (100, 100, 200), 2)
                if ts - self.m_start_ts > self.m_duration:
                    self.stop()
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            a = QImage(frame.data, frame.shape[1], frame.shape[0], QImage.Format_RGB888)
            self.m_camera_list[idx]['show_label'].setPixmap(QPixmap.fromImage(a))
            self.m_camera_list[idx]['show_label'].setScaledContents(True)

    def closeEvent(self, event):
        result = QtWidgets.QMessageBox.question(self, "Close rPPGCollectTool", "Are you sure to close?",
                                                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if result == QtWidgets.QMessageBox.Yes:
            for i in range(len(self.m_camera_list)):
                self.m_camera_list[i]['get_video'].stop()
                self.m_camera_list[i]['save_video'].stop()
            self.m_pulse_saver.stop()
            self.m_ppg_receiver.stop()
            self.m_update_graph_timer.stop()
            self.m_audio_recorder.stop()
            event.accept()
        else:
            event.ignore()

if __name__ == '__main__':
    import sys

    app = QtWidgets.QApplication(sys.argv)
    demo = rPPGCollectTool()
    demo.show()
    sys.exit(app.exec_())

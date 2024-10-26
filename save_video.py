import time
from PySide6.QtCore import QThread
import cv2
import os
import numpy as np
import subprocess
from log import logger


class SaveVideo(QThread):
    def __init__(self):
        super(SaveVideo, self).__init__()
        self.m_stop = True
        self.m_final_stop = True
        self.m_frames = []
        self.m_save_path = ''
        self.m_fps = 30
        self.m_h = 480
        self.m_w = 720
        self.m_name = ""
        self.m_key = None
        self.m_format = '.avi'

        self.m_video_save_format_list = []
        self.m_image_save_format_list = []

    def init(self):
        try:
            self.m_key = None
            self.m_frames.clear()
            with open(self.m_save_path + f'/{self.m_name}_timestamp.txt', 'w') as f:
                f.write("")
        except Exception as e:
            logger.error("[save video] init error! " + str(e))

    def setKey(self, key):
        if self.m_key is None:
            self.m_key = key
            cv2.imwrite(self.m_save_path + f'/{self.m_name}_key.png', key)

    def addFrame(self, ts, frame):
        self.m_frames.append([ts, frame])

    def setParams(self, save_path, save_format_list, fps, h, w, name):
        '''
            save_format_list:   the format for save video
            fps:                the fps for save video
            h:                  the height of save video
            w:                  the width of save video
            name:               the name of save video
        '''
        self.m_save_path = save_path
        self.m_fps = fps
        self.m_h = h
        self.m_w = w
        self.m_video_save_format_list.clear()
        self.m_image_save_format_list.clear()
        for _format in save_format_list:
            if _format in ['MJPG', 'FFV1']:
                self.m_video_save_format_list.append(_format)
            elif _format in ['PNG']:
                self.m_image_save_format_list.append(_format)
        self.m_name = name

    def stop(self):
        self.m_stop = True

    def run(self):
        self.init()
        # ---------------------------------------------------------------------#
        #   create video_writer for each format
        # ---------------------------------------------------------------------#
        try:
            video_out_list = []
            for _format in self.m_video_save_format_list:
                fourcc = cv2.VideoWriter_fourcc(*_format)
                video_file = f'{self.m_save_path}/_{self.m_name}_{_format}{self.m_format}'
                if os.path.exists(video_file):
                    os.remove(video_file)
                out = cv2.VideoWriter(video_file, fourcc, self.m_fps, (self.m_w, self.m_h), True)
                video_out_list.append(out)
        except Exception as e:
            logger.error("[save video] create video_writer for each format failed! " + str(e))
        # ---------------------------------------------------------------------#
        #   create path for saving pictures
        # ---------------------------------------------------------------------#
        image_out_path_list = []
        for _format in self.m_image_save_format_list:
            path = f'{self.m_save_path}/images_{self.m_name}_{_format}/'
            if not os.path.exists(path):
                os.mkdir(path)
            image_out_path_list.append([path, _format])
        self.m_stop = False
        self.m_final_stop = False
        frame_count = 0
        while 1:
            is_work = False
            if self.m_stop and len(self.m_frames) == 0:
                break
            if len(self.m_frames) > 0:
                # ---------------------------------------------------------------------#
                #   get the first frame in caches for saving, then drop it from caches
                # ---------------------------------------------------------------------#
                ts, frame = self.m_frames.pop(0)
                if frame.shape[:2] != (self.m_h, self.m_w):
                    frame = cv2.resize(frame, (self.m_w, self.m_h))
                # ---------------------------------------------------------------------#
                #   save videos
                # ---------------------------------------------------------------------#
                for video_out in video_out_list:
                    video_out.write(frame)
                # ---------------------------------------------------------------------#
                #   save pictures
                # ---------------------------------------------------------------------#
                for image_path in image_out_path_list:
                    cv2.imwrite(image_path[0] + f'{frame_count}.{image_path[1]}', frame)
                # ---------------------------------------------------------------------#
                #   save the timestamp for each frame
                # ---------------------------------------------------------------------#
                with open(self.m_save_path + f'/{self.m_name}_timestamp.txt', 'a+') as f:
                    f.write('%f %d\n' % (ts, frame_count))
                frame_count += 1
                is_work = True

            if not is_work:
                time.sleep(1)

        for video_out in video_out_list:
            video_out.release()

        try:
            for _format in self.m_video_save_format_list:
                if os.path.exists(f'{self.m_save_path}/_{self.m_name}_{_format}{self.m_format}'):
                    data = np.loadtxt(self.m_save_path + f'/{self.m_name}_timestamp.txt', dtype=float)
                    fps = len(data) / (data[-1, 0] - data[0, 0])
                    if abs(fps - self.m_fps) <= 1:
                        os.rename(f'{self.m_save_path}/_{self.m_name}_{_format}{self.m_format}',
                                  f'{self.m_save_path}/{self.m_name}_{_format}{self.m_format}')
                        continue

                    fourcc = cv2.VideoWriter_fourcc(*_format)
                    out = cv2.VideoWriter(f'{self.m_save_path}/{self.m_name}_{_format}{self.m_format}', fourcc, fps,
                                        (self.m_w, self.m_h), True)

                    cap = cv2.VideoCapture(f'{self.m_save_path}/_{self.m_name}_{_format}{self.m_format}')
                    while 1:
                        ret, frame = cap.read()
                        if not ret:
                            break
                        out.write(frame)
                    cap.release()
                    out.release()
                    os.remove(f'{self.m_save_path}/_{self.m_name}_{_format}{self.m_format}')
        except Exception as e:
            logger.error("[save video] check fps error! " + str(e))

        try:
            audio_file = f'{self.m_save_path}/audio.wav'
            if os.path.exists(audio_file):
                for _format in self.m_video_save_format_list:
                    video_file = f'{self.m_save_path}/{self.m_name}_{_format}{self.m_format}'
                    if os.path.exists(video_file):
                        self.convert_video_audio(video_file, audio_file)
        except Exception as e:
            logger.error("[save video] add video error! " + str(e))

        self.m_final_stop = True

    def convert_video_audio(self, video_file, audio_file):
        out_file = video_file[:-4] + '-with-audio' + self.m_format
        if os.path.exists(out_file):
            os.remove(out_file)
        # cmd = f"ffmpeg -i {video_file} -i {audio_file} -c:v copy -c:a aac -strict experimental -map 0:v:0 -map 1:a:0 {out_video_file}"

        # 构造FFmpeg命令
        ffmpeg_cmd = [
            'ffmpeg/ffmpeg',
            '-i', video_file,
            '-i', audio_file,
            '-c:v', 'copy',  # 复制视频流，不进行重新编码
            '-c:a', 'aac',  # 使用AAC编码音频流
            '-strict', 'experimental',  # 在某些FFmpeg版本中可能需要这个选项
            '-map', '0:v:0',  # 选择第一个输入文件（视频文件）中的第一个视频流
            '-map', '1:a:0',  # 选择第二个输入文件（音频文件）中的第一个音频流
            out_file
        ]

        # 调用FFmpeg命令
        try:
            subprocess.run(ffmpeg_cmd, check=True)
            print(f"FFmpeg command succeeded. Output file: {out_file}")
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg command failed with error: {e}")
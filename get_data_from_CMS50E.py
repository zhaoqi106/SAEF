import hid
import time
from PySide6.QtCore import QThread, Signal


class GetDataFromCMS50E(QThread):
    signal_data = Signal(dict)

    def __init__(self):
        super(GetDataFromCMS50E, self).__init__()
        self.m_stop = True

    def run(self):
        h = None
        self.m_stop = False
        while not self.m_stop:
            try:
                vid, pid = 0, 0
                for i in hid.enumerate():
                    if i['product_string'] == 'Pulse Oximeter':
                        vid, pid = i['vendor_id'], i['product_id']
                        if h is not None:
                            h.close()
                        h = hid.device()
                        h.open(vid, pid)
                        break
                        
                if vid == 0 and pid == 0:
                    self.signal_data.emit({'ret': -1, 'msg': 'No pulse oximeter found!'})
                    time.sleep(1)
                else:
                    break
            except:
                pass

        while not self.m_stop:
            try:
                recv = h.read(30)
                msgs = []
                recv_data = {'ret': 0, 'msg': '', 'ts': None, 'hr': [], 'spo2': [], 'ppg': []}
                t = time.time()
                recv_data['ts'] = t
                for i in recv:
                    if i == 235:
                        msgs.append([])
                        continue
                    msgs[-1].append(i)
                for i in msgs:
                    if i[:1] == [0]:
                        recv_data['ppg'].append(i[2])
                    if i[:2] == [1, 5]:
                        _2, _3 = i[2], i[3]
                        recv_data['hr'].append(_2)
                        recv_data['spo2'].append(_3)
                self.signal_data.emit(recv_data)
            except:
                pass

        try:
            if h:
                h.close()

            self.signal_data.emit({'ret': -1, 'msg': 'Stop getting pulse oximeter dara!'})
        except:
            ...

    def stop(self):
        self.m_stop = True

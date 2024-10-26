import numpy as np
import os
import tkinter
from tkinter import messagebox

if __name__ == '__main__':
    root = tkinter.Tk()
    root.withdraw()  # 隐藏主窗口
    all_file = os.listdir()
    file_list = [filename for filename in all_file if filename.endswith('timestamp.txt')]
    if len(file_list) == 0:
        messagebox.showinfo("警告", "当前目录没有找到xxx-timestamp.txt文件！")
    elif 'ppg.txt' in all_file:
        ppg = np.loadtxt('ppg.txt', dtype=float)
        ppg_ts = ppg[:, 0]
        ppg = ppg[:, 1]
        for filename in file_list:
            data = np.loadtxt(filename, dtype=float)
            frame_ts = data[:, 0]
            frame_idx = data[:, 1]
            new_ppg = np.interp(frame_ts, ppg_ts, ppg)
            with open(filename[:-4] + '-ppg.txt', 'w') as f:
                for i in range(len(new_ppg)):
                    f.write("%d %.2f\n" % (int(frame_idx[i]), new_ppg[i]))
        messagebox.showinfo("提示", "完成转换！")
    else:
        messagebox.showinfo("警告", "当前目录没有找到ppg.txt文件！")

import numpy as np
import os
from scipy.interpolate import interp1d

if __name__ == '__main__':
    all_file = os.listdir()
    file_list = [filename for filename in all_file if filename.endswith('timestamp.txt')]
    if 'ppg.txt' in all_file:
        ppg = np.loadtxt('ppg.txt', dtype=float)
        ppg_ts = ppg[:, 0]
        ppg = ppg[:, 1]
        func = interp1d(ppg_ts, ppg)
        for filename in file_list:
            data = np.loadtxt(filename, dtype=float)
            frame_ts = data[:, 0]
            frame_idx = data[:, 1]
            new_ppg = func(frame_ts)
            with open(filename[:-4] + '-ppg.txt', 'w') as f:
                for i in range(len(new_ppg)):
                    f.write("%d %.2f\n" % (int(frame_idx[i]), new_ppg[i]))

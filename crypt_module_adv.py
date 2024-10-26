import random
import cv2
import numpy as np
import time
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Cipher import DES

# Key for encryption and decryption
teakey = [0x11234567, 0x89ab1def, 0xfedcba98, 0x76543210]
otherkey = bytes([0x11, 0x23, 0x45, 0x67, 0x89, 0xab, 0x1d, 0xef, 0xfe, 0xdc, 0xba, 0x98, 0x76, 0x54, 0x32, 0x10])
xorkey = np.array([[0x0e, 0x3d, 0x10, 0xbf, 0x14, 0x03, 0xb9, 0xcb, 0x95, 0xfa, 0xb5, 0xce, 0x70, 0xd8, 0xd2, 0xe4]],
                  dtype=np.uint8)


def uint8Array2uint32_adv(data):
    new_data = np.array(data, dtype=np.uint32)
    ret = new_data[:, 0] * 16777216 + new_data[:, 1] * 65536 + new_data[:, 2] * 256 + new_data[:, 3]
    return ret


def uint322uint8array_adv(data):
    result = np.empty((len(data), 4), dtype=np.uint8)
    for i in range(4):
        result[:, i] = 0x000000ff & (data >> 8 * (3 - i))
    return result


def des_encrypt(data, key=otherkey):
    # initialize AES cipher
    cipher = DES.new(key[:8], DES.MODE_ECB)
    # encrypt the plaintext
    data = data.tobytes()
    encrypted_data = cipher.encrypt(data)
    return np.frombuffer(encrypted_data, dtype=np.uint8)


def des_decrypt(data, key=otherkey):
    # initialize AES cipher
    cipher = DES.new(key[:8], DES.MODE_ECB)
    # encrypt the plaintext
    data = data.tobytes()
    decrypted_data = cipher.decrypt(data)
    return np.frombuffer(decrypted_data, dtype=np.uint8)


def aes_encrypt(data, key=otherkey):
    # initialize AES cipher
    cipher = AES.new(key, AES.MODE_ECB)
    # encrypt the plaintext
    data = data.tobytes()
    encrypted_data = cipher.encrypt(data)
    return np.frombuffer(encrypted_data, dtype=np.uint8)


def aes_decrypt(data, key=otherkey):
    # initialize AES cipher
    cipher = AES.new(key, AES.MODE_ECB)
    # encrypt the plaintext
    data = data.tobytes()
    decrypted_data = cipher.decrypt(data)
    return np.frombuffer(decrypted_data, dtype=np.uint8)


def tea_encrypt_adv(data, key=teakey):
    valid_num = len(data)
    delta = 0x9e3779b9
    mask = 0xffffffff
    v0 = uint8Array2uint32_adv(data[:valid_num // 2].reshape((-1, 4)))
    v1 = uint8Array2uint32_adv(data[valid_num // 2:].reshape((-1, 4)))
    sum = 0
    for _ in range(32):
        sum = (sum + delta) & mask
        v0 += ((v1 << 4) + key[0]) ^ (v1 + sum) ^ ((v1 >> 5) + key[1])
        v0 &= mask
        v1 += ((v0 << 4) + key[2]) ^ (v0 + sum) ^ ((v0 >> 5) + key[3])
        v1 &= mask
    encrypted_data = np.hstack((uint322uint8array_adv(v0).ravel(), uint322uint8array_adv(v1).ravel()))
    return encrypted_data


def tea_decrypt_adv(data, key=teakey):
    valid_num = len(data)
    delta = 0x9e3779b9
    mask = 0xffffffff
    v0 = uint8Array2uint32_adv(data[:valid_num // 2].reshape((-1, 4)))
    v1 = uint8Array2uint32_adv(data[valid_num // 2:].reshape((-1, 4)))
    sum = (delta * 32) & mask
    for _ in range(32):
        v1 -= ((v0 << 4) + key[2]) ^ (v0 + sum) ^ ((v0 >> 5) + key[3])
        v1 &= mask
        v0 -= ((v1 << 4) + key[0]) ^ (v1 + sum) ^ ((v1 >> 5) + key[1])
        v0 &= mask
        sum = (sum - delta) & mask

    decrypted_data = np.hstack((uint322uint8array_adv(v0).ravel(), uint322uint8array_adv(v1).ravel()))
    return decrypted_data


def xor_encrypty(data, key=xorkey):
    xorData = data.reshape((-1, 8)) ^ xorkey[:, :8]
    xorData = xorData + xorkey[:, 8:]
    return xorData.ravel()


def xor_decrypty(encrypted_data, key=xorkey):
    data = encrypted_data.reshape((-1, 8)) - xorkey[:, 8:]
    data = data ^ xorkey[:, :8]
    return data.ravel()


def xor_encrypty_adv(data, key=xorkey):
    # return data ^ key;
    return cv2.bitwise_xor(data, key)

def xor_decrypty_adv(data, key=xorkey):
    # return data ^ key;
    return cv2.bitwise_xor(data, key)

def hide_encrypt_arrays(data, algNum=1, key=teakey):
    valid_num = len(data) // 8
    valid_num = valid_num * 8
    res_num = len(data) - valid_num
    if algNum == 1:
        # encrypted_data = xor_encrypty(data[:valid_num])
        encrypted_data = xor_encrypty_adv(data, key)
        res_num = 0
    else:
        if algNum == 2:
            encrypted_data = tea_encrypt_adv(data[:valid_num], key)
        elif algNum == 3:
            encrypted_data = aes_encrypt(data[:valid_num], bytes(key))
        elif algNum == 4:
            encrypted_data = des_encrypt(data[:valid_num], bytes(key))

        if res_num > 0:
            encrypted_data = np.hstack((encrypted_data, data[-res_num:]))

    return encrypted_data


def hide_decrypt_arrays(data, algNum=1, key=teakey):
    valid_num = len(data) // 8
    valid_num = valid_num * 8
    res_num = len(data) - valid_num
    if algNum == 1:
        # decrypt_data = xor_decrypty(data[:valid_num])
        decrypt_data = xor_decrypty_adv(data, key)
        res_num = 0
    else:
        if algNum == 2:
            decrypt_data = tea_decrypt_adv(data[:valid_num], key)
        elif algNum == 3:
            decrypt_data = aes_decrypt(data[:valid_num], bytes(key))
        elif algNum == 4:
            decrypt_data = des_decrypt(data[:valid_num], bytes(key))
        if res_num > 0:
            decrypt_data = np.hstack((decrypt_data, data[-res_num:]))

    return decrypt_data


def test(filename):
    import os
    if os.path.isfile(filename):
        cap = cv2.VideoCapture(filename)
        frame_list = []
        while 1:
            ret, frame = cap.read()
            if not ret:
                break
            frame_list.append(frame)
            if len(frame_list) == 100:
                break
        cap.release()
    else:
        file_list = [image_file for image_file in os.listdir(filename) if image_file[-4:] in ['.jpg', '.png']]
        frame_list = []
        for i in range(len(file_list)):
            frame = cv2.imdecode(np.fromfile(filename + '/' + file_list[i], dtype=np.uint8), -1)
            frame_list.append(frame)
            if len(frame_list) == 20:
                break

    leg = len(frame_list)
    imageSize = frame_list[0].shape
    # cv2.imshow("Origin",frame_list[0])
    key1 = hide_encrypt_arrays(frame_list[0].ravel(), 3)
    imageVector = np.array([a for a in key1]).astype(np.uint8)
    key1 = imageVector.reshape(imageSize)
    # cv2.imshow("de",key1)
    #  cv2.waitKey(0)

    t1 = time.time()
    for frame in frame_list:
        # hide_encrypt_arrays(frame.ravel(), 1, frame_list[0].ravel())
        image = cv2.bitwise_xor(frame, key1)  # xor(frame, key)
    t2 = time.time()
    print("XOR加密耗时：%.8f秒/%d 张，平均每张图片耗时：%.8f" % (t2 - t1, leg, (t2 - t1) / leg))

    t1 = time.time()
    for frame in frame_list:
        hide_encrypt_arrays(frame.ravel(), 2)
    t2 = time.time()
    print("TEA加密耗时：%.8f秒/%d 张，平均每张图片耗时：%.8f" % (t2 - t1, leg, (t2 - t1) / leg))

    t1 = time.time()
    for frame in frame_list:
        hide_encrypt_arrays(frame.ravel(), 3)
    t2 = time.time()
    print("AES加密耗时：%.8f秒/%d 张，平均每张图片耗时：%.8f" % (t2 - t1, leg, (t2 - t1) / leg))

    t1 = time.time()
    for frame in frame_list:
        hide_encrypt_arrays(frame.ravel(), 3)
    t2 = time.time()
    print("DES加密耗时：%.8f秒/%d 张，平均每张图片耗时：%.8f" % (t2 - t1, leg, (t2 - t1) / leg))

def encrypt_image(img, alg_num, key, mask=None):
    if alg_num == 1:
        if mask is None:
            imageSize = img.shape
            imageVector = img.reshape(-1)
            imageVector = hide_encrypt_arrays(imageVector, 2, key)
            image = imageVector.reshape(imageSize)
        else:
            image = hide_encrypt_arrays(img, alg_num, mask)
    else:
        imageSize = img.shape
        imageVector = img.reshape(-1)
        imageVector = hide_encrypt_arrays(imageVector, alg_num, key)
        image = imageVector.reshape(imageSize)
    return image

def decrypt_image(img, alg_num, key):
    imageSize = img.shape
    imageVector = img.reshape(-1)
    imageVector = hide_decrypt_arrays(imageVector, True, tea_key, xor_key)
    imageVector = np.array([a for a in imageVector]).astype(np.uint8)
    image = imageVector.reshape(imageSize)
    return image

# def test07():
#     re_test_num = 100


#     img = cv2.imread("save_data/01.png")
#     xor_key = cv2.imread("save_data/key.png").ravel()
#     print(img.shape)
#     # XOR算法
#     t1 = time.time()
#     for _ in range(re_test_num):
#         en_img = hide_encrypt_arrays(img.ravel(), 1, xor_key)
#     t2 = time.time()
#     print("XOR加密用时：%f s" % ((t2-t1)/re_test_num))
#     en_img = en_img.reshape(img.shape)
#     t1 = time.time()
#     for _ in range(re_test_num):
#         de_img = hide_decrypt_arrays(en_img.ravel(), 1, xor_key)
#     t2 = time.time()
#     print("XOR解密用时：%f s\n" % ((t2-t1)/re_test_num))
#     de_img = de_img.reshape(img.shape)

#     xor_img = np.hstack((img, en_img, de_img))
#     cv2.namedWindow("XOR", cv2.WINDOW_NORMAL)
#     cv2.imshow("XOR", xor_img)
#     # cv2.waitKey(0)


#     # TEA算法
#     t1 = time.time()
#     for _ in range(re_test_num):
#         en_img = hide_encrypt_arrays(img.ravel(), 2)
#     t2 = time.time()
#     print("TEA加密用时：%f s" % ((t2-t1)/re_test_num))
#     en_img = en_img.reshape(img.shape)
#     t1 = time.time()
#     for _ in range(re_test_num):
#         de_img = hide_decrypt_arrays(en_img.ravel(), 2)
#     t2 = time.time()
#     print("TEA解密用时：%f s\n" % ((t2-t1)/re_test_num))
#     de_img = de_img.reshape(img.shape)

#     xor_img = np.hstack((img, en_img, de_img))
#     cv2.namedWindow("TEA", cv2.WINDOW_NORMAL)
#     cv2.imshow("TEA", xor_img)
#     # cv2.waitKey(0)


#     # AES算法
#     t1 = time.time()
#     for _ in range(re_test_num):
#         en_img = hide_encrypt_arrays(img.ravel(), 3)
#     t2 = time.time()
#     print("AES加密用时：%f s" % ((t2-t1)/re_test_num))
#     en_img = en_img.reshape(img.shape)
#     t1 = time.time()
#     for _ in range(re_test_num):
#         de_img = hide_decrypt_arrays(en_img.ravel(), 3)
#     t2 = time.time()
#     print("AES解密用时：%f s\n" % ((t2-t1)/re_test_num))
#     de_img = de_img.reshape(img.shape)

#     aes_img = np.hstack((img, en_img, de_img))
#     cv2.namedWindow("AES", cv2.WINDOW_NORMAL)
#     cv2.imshow("AES", aes_img)
#     # cv2.waitKey(0)

#     # DES算法
#     t1 = time.time()
#     for _ in range(re_test_num):
#         en_img = hide_encrypt_arrays(img.ravel(), 3)
#     t2 = time.time()
#     print("DES加密用时：%f s" % ((t2-t1)/re_test_num))
#     en_img = en_img.reshape(img.shape)
#     t1 = time.time()
#     for _ in range(re_test_num):
#         de_img = hide_decrypt_arrays(en_img.ravel(), 3)
#     t2 = time.time()
#     print("DES解密用时：%f s\n" % ((t2-t1)/re_test_num))
#     de_img = de_img.reshape(img.shape)

#     des_img = np.hstack((img, en_img, de_img))
#     cv2.namedWindow("DES", cv2.WINDOW_NORMAL)
#     cv2.imshow("DES", aes_img)
#     cv2.waitKey(0)


def test10(filename):
    cap = cv2.VideoCapture(filename)
    total_frame_num = cap.get(7)
    print(total_frame_num)

    cap.release()


if __name__ == "__main__":
    # test(r"E:\测试视频\PURE-01")
    # test10(r"F:\厦门大学\ADA-yolo\data\test03\测试视频\UBFC-rPPG-01.avi")
    test10(r"G:\UBFC-rppg\subject1\vid.avi")

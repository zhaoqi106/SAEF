import cv2
import numpy as np
import time

# Key for encryption and decryption


def tea_encrypt(data, key):
    delta = 0x9e3779b9
    mask = 0xffffffff
    v0, v1 = int.from_bytes(data[:4], 'big'), int.from_bytes(data[4:], 'big')
    k0, k1, k2, k3 = int.from_bytes(key[:4], 'big'), int.from_bytes(key[4:8], 'big'), int.from_bytes(key[8:12], 'big'), int.from_bytes(key[12:], 'big')
    sum = 0
    
    for _ in range(32):
        sum = (sum + delta) & mask
        v0 += ((v1 << 4) + k0) ^ (v1 + sum) ^ ((v1 >> 5) + k1)
        v0 &= mask
        v1 += ((v0 << 4) + k2) ^ (v0 + sum) ^ ((v0 >> 5) + k3)
        v1 &= mask
    
    encrypted_data = v0.to_bytes(4, 'big') + v1.to_bytes(4, 'big')
    return encrypted_data

def tea_decrypt(encrypted_data, key):
    delta = 0x9e3779b9
    mask = 0xffffffff
    v0, v1 = int.from_bytes(encrypted_data[:4], 'big'), int.from_bytes(encrypted_data[4:], 'big')
    k0, k1, k2, k3 = int.from_bytes(key[:4], 'big'), int.from_bytes(key[4:8], 'big'), int.from_bytes(key[8:12], 'big'), int.from_bytes(key[12:], 'big')
    sum = (delta * 32) & mask
    
    for _ in range(32):
        v1 -= ((v0 << 4) + k2) ^ (v0 + sum) ^ ((v0 >> 5) + k3)
        v1 &= mask
        v0 -= ((v1 << 4) + k0) ^ (v1 + sum) ^ ((v1 >> 5) + k1)
        v0 &= mask
        sum = (sum - delta) & mask
    
    decrypted_data = v0.to_bytes(4, 'big') + v1.to_bytes(4, 'big')
    return decrypted_data

def xor_encrypty(data, xorkey):
    xorData = bytes(a ^ b for a, b in zip(data, xorkey[0:len(data)]))
    xorData = bytes((0x100-b+a)%256 for a, b in zip(xorData, xorkey[(len(xorkey)-len(data)):]))
    return xorData

def xor_decrypty(encrypted_data, xorkey):
    data = bytes((a+b)%256 for a, b in zip(encrypted_data, xorkey[(len(xorkey)-len(encrypted_data)):]))
    data = bytes(a ^ b for a, b in zip(data, xorkey[0:len(data)]))
    return data

def bytes2HexString(stream):
    hex_string = " ".join(hex(byte)[2:].zfill(2) for byte in stream)
    return hex_string
    
def hide_encrypt_arrays(data, teaFlag, teakey, xorkey):
    dataLen = len(data)
    encrypted_data = bytes(0)
    teaLen = dataLen // 8
    xorData = data[teaLen*8:]
    for i in range(teaLen):
        if False == teaFlag:
            encrypted_data = encrypted_data + xor_encrypty(data[i*8:(i+1)*8],teakey)
        else:
            encrypted_data = encrypted_data + tea_encrypt(data[i*8:(i+1)*8],teakey)
    xorData = xor_encrypty(xorData,xorkey)
    encrypted_data = encrypted_data + xorData
    return encrypted_data

def hide_decrypt_arrays(data, teaFlag, tea_key, xor_key):
    dataLen = len(data)
    decrypt_data = bytes(0)
    teaLen = dataLen // 8
    xorData = data[teaLen*8:]
    for i in range(dataLen//8):
        if False == teaFlag:
            decrypt_data = decrypt_data + xor_decrypty(data[i*8:(i+1)*8],tea_key)
        else:
            decrypt_data = decrypt_data + tea_decrypt(data[i*8:(i+1)*8],tea_key)
    xorData = xor_decrypty(xorData,xor_key)
    decrypt_data = decrypt_data + xorData
    return decrypt_data

def encrypt_image(img, tea_key, xor_key):
    imageSize = img.shape
    imageVector = img.reshape(-1)
    imageVector = hide_encrypt_arrays(imageVector, True, tea_key, xor_key)
    imageVector = np.array([a for a in imageVector]).astype(np.uint8)
    image = imageVector.reshape(imageSize)
    return image

def decrypt_image(img, tea_key, xor_key):
    imageSize = img.shape
    imageVector = img.reshape(-1)
    imageVector = hide_decrypt_arrays(imageVector, True, tea_key, xor_key)
    imageVector = np.array([a for a in imageVector]).astype(np.uint8)
    image = imageVector.reshape(imageSize)
    return image

def encrypt(img, org_img=None):
    if org_img is not None:
        en_img = img - org_img
    else:
        en_img = encrypt_image(img)
    return en_img
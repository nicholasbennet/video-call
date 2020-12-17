import cv2
from socket import socket, AF_INET, SOCK_STREAM
import pyaudio
from threading import Thread
import numpy as np
import struct
import tkinter as Tk
import math

HOST = '52.21.167.84'
PORT_VIDEO = 3000
PORT_AUDIO = 4000

BufferSize = 4096
CHUNK=1024
lnF = 640*480*3
FORMAT=pyaudio.paInt16
CHANNELS=1
RATE=44100

CONTINUE = True
QUIT = False

VFILTER = "Normal"
VFILTERS = [
    "Normal",
    "Sharpen",
    "Sepia",
    "Gaussian Blur",
    "Emboss"
]

AFILTER = "Normal"
AFILTERS = [
    "Normal",
    "Amplitude Modulation",
    "Vibrato"
]

# Video Filters

def normal (image):
    return image

def sharpen(image):
    kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    return cv2.filter2D(image, -1, kernel)

def sepia(image):
    kernel = np.array([[0.272, 0.534, 0.131],
                       [0.349, 0.686, 0.168],
                       [0.393, 0.769, 0.189]])
    return cv2.filter2D(image, -1, kernel)

def gaussianBlur(image):
    return cv2.GaussianBlur(image, (35, 35), 0)

def emboss(image):
    kernel = np.array([[0,-1,-1],
                            [1,0,-1],
                            [1,1,0]])
    return cv2.filter2D(image, -1, kernel)

# Audio Filters

def anormal(data):
    return data

def clip16( x ):
    if x > 32767:
        x = 32767
    elif x < -32768:
        x = -32768
    else:
        x = x        
    return(x)


f0 = 400
output_block = CHUNK * [0]
om = 2*math.pi*f0/RATE
theta = 0
def ammod(data):
    global theta
    input_tuple = struct.unpack('h' * CHUNK, data)
    for n in range(0, CHUNK):
        theta = theta + om
        output_block[n] = int( input_tuple[n] * math.cos(theta) )
    while theta > math.pi:
        theta = theta - 2*math.pi
    output_bytes = struct.pack('h' * CHUNK, *output_block)
    return output_bytes


n = 0
BUFFER_LEN =  1024
f0 = 2
W = 0.2
buffer = BUFFER_LEN * [0]
kr = 0
kw = int(0.5 * BUFFER_LEN)
def vibrato(data):
    global n, kr, kw, buffer
    input_tuple = struct.unpack('h' * CHUNK, data)
    for k in range(0, CHUNK):
        kr_prev = int(math.floor(kr))
        frac = kr - kr_prev
        kr_next = kr_prev + 1
        if kr_next == BUFFER_LEN:
            kr_next = 0
        y0 = (1-frac) * buffer[kr_prev] + frac * buffer[kr_next]
        buffer[kw] = input_tuple[k]
        kr = kr + 1 + W * math.sin( 2 * math.pi * f0 * n / RATE )
        if kr >= BUFFER_LEN:
            kr = kr - BUFFER_LEN
        kw = kw + 1
        if kw == BUFFER_LEN:
            kw = 0
        output_block[k] = int(clip16(y0))
        if n == (CHUNK * 2):
            n = 0
        else:
            n+=1
    output_bytes = struct.pack('h' * CHUNK, *output_block)
    return output_bytes

# Audio transmission

def SendAudio():
    while True:
        data = stream.read(CHUNK)
        if AFILTER == "Normal":
            data = anormal(data)
        elif AFILTER == "Amplitude Modulation":
            data = ammod(data)
        elif AFILTER == "Vibrato":
            data == vibrato(data)
        else:
            data = anormal(data)
        clientAudioSocket.sendall(data)
        if QUIT:
            break

# Audio recieving

def RecieveAudio():
    while True:
        data = recvallAudio(BufferSize)
        stream.write(data)
        if QUIT:
            break

def recvallAudio(size):
    databytes = b''
    while len(databytes) != size:
        to_read = size - len(databytes)
        if to_read > (4 * CHUNK):
            databytes += clientAudioSocket.recv(4 * CHUNK)
        else:
            databytes += clientAudioSocket.recv(to_read)
    return databytes

# Video transmission

def SendFrame():
    while True:
        try:
            _, frame = cap.read()
            frame = cv2.flip(frame, 1)
            frame = cv2.resize(frame, (640, 480))
            if VFILTER == "Normal":
                frame = normal(frame)
            elif VFILTER == "Sharpen":
                frame = sharpen(frame)
            elif VFILTER == "Sepia":
                frame = sepia(frame)
            elif VFILTER == "Gaussian Blur":
                frame = gaussianBlur(frame)
            elif VFILTER == "Emboss":
                frame = emboss(frame)
            else:
                frame = normal(frame)
            is_success, im_buf_arr = cv2.imencode(".jpg", frame)
            databytes = im_buf_arr.tobytes()
            cv2.imshow("Host", frame)
            if cv2.waitKey(1) == 27:
                    cv2.destroyAllWindows()
            length = struct.pack('!I', len(databytes))
            bytesToBeSend = b''
            clientVideoSocket.sendall(length)
            while len(databytes) > 0:
                if (5000 * CHUNK) <= len(databytes):
                    bytesToBeSend = databytes[:(5000 * CHUNK)]
                    databytes = databytes[(5000 * CHUNK):]
                    clientVideoSocket.sendall(bytesToBeSend)
                else:
                    bytesToBeSend = databytes
                    clientVideoSocket.sendall(bytesToBeSend)
                    databytes = b''
        except:
            continue
        if QUIT:
            break
    
# Video recieving

def RecieveFrame():
    while True:
        try:
            lengthbuf = recvallVideo(4)
            length, = struct.unpack('!I', lengthbuf)
            databytes = recvallVideo(length)
            if len(databytes) == length:
                nparr = np.frombuffer(databytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                cv2.imshow("Client", img)
                if cv2.waitKey(1) == 27:
                    cv2.destroyAllWindows()
        except:
            continue
        if QUIT:
            break

def recvallVideo(size):
    databytes = b''
    while len(databytes) != size:
        to_read = size - len(databytes)
        if to_read > (5000 * CHUNK):
            databytes += clientVideoSocket.recv(5000 * CHUNK)
        else:
            databytes += clientVideoSocket.recv(to_read)
    return databytes

# Quit Button

def end_call():
  global CONTINUE
  global QUIT
  print('Good bye')
  CONTINUE = False
  cap.release()
  cv2.destroyAllWindows()
  stream.stop_stream()
  stream.close()
  QUIT = True
  SendFrameThread.join()
  SendAudioThread.join()
  RecieveFrameThread.join()
  RecieveAudioThread.join()
  clientAudioSocket.close()
  clientVideoSocket.close()

# UI Controls

root = Tk.Tk()
root.wm_title("Video Call Controls")

# Quit Button
B_quit = Tk.Button(root, text = 'Quit', command = end_call, anchor='e')
B_quit.grid(row=2, column=1, padx=10, pady=2)

# Video Dropdown Menu
vdropdownLabel = Tk.Label(root, text="Video Filter:", anchor='w')
vdropdownLabel.grid(row=0, column=0, padx=10, pady=2)
vlistvar = Tk.StringVar(root)
vlistvar.set(VFILTERS[0])
vdropdown = Tk.OptionMenu(root, vlistvar, *VFILTERS)
vdropdown.grid(row=0, column=1, padx=10, pady=2)

# Audio Dropdown Menu
adropdownLabel = Tk.Label(root, text="Audio Filter:", anchor='w')
adropdownLabel.grid(row=1, column=0, padx=10, pady=2)
alistvar = Tk.StringVar(root)
alistvar.set(AFILTERS[0])
adropdown = Tk.OptionMenu(root, alistvar, *AFILTERS)
adropdown.grid(row=1, column=1, padx=10, pady=2)

# Socket definition

clientVideoSocket = socket(family=AF_INET, type=SOCK_STREAM)
clientVideoSocket.connect((HOST, PORT_VIDEO))
cap = cv2.VideoCapture(0)

clientAudioSocket = socket(family=AF_INET, type=SOCK_STREAM)
clientAudioSocket.connect((HOST, PORT_AUDIO))
audio=pyaudio.PyAudio()
stream=audio.open(format=FORMAT,channels=CHANNELS, rate=RATE, input=True, output = True,frames_per_buffer=CHUNK)

# Initiating connection

initiation = clientVideoSocket.recv(5).decode()

# Initiating audio and video threads

SendFrameThread = Thread(target=SendFrame)
SendAudioThread = Thread(target=SendAudio)
RecieveFrameThread = Thread(target=RecieveFrame)
RecieveAudioThread = Thread(target=RecieveAudio)

if initiation == "start":
    SendFrameThread.start()
    SendAudioThread.start()
    RecieveFrameThread.start()
    RecieveAudioThread.start()

# Loop to update UI

while CONTINUE:
    VFILTER = vlistvar.get()
    AFILTER = alistvar.get()
    root.update()

import cv2
from socket import socket, AF_INET, SOCK_STREAM
import pyaudio
from threading import Thread
import numpy as np
import struct
import tkinter as Tk
from PIL import Image, ImageTk

HOST = '52.21.167.84'
PORT_VIDEO = 3000
PORT_AUDIO = 4000

BufferSize = 4096
CHUNK=1024
lnF = 640*480*3
FORMAT=pyaudio.paInt16
CHANNELS=2
RATE=44100

CONTINUE = True
QUIT = False

def SendAudio():
    while True:
        data = stream.read(CHUNK, exception_on_overflow = False)
        clientAudioSocket.sendall(data)
        global QUIT
        if QUIT:
            break

def RecieveAudio():
    while True:
        data = recvallAudio(BufferSize)
        stream.write(data)
        global QUIT
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

def SendFrame():
    while True:
        try:
            _, frame = cap.read()
            frame = cv2.flip(frame, 1)
            frame = cv2.resize(frame, (640, 480))
            cv2_im = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
            is_success, im_buf_arr = cv2.imencode(".jpg", cv2_im)
            databytes = im_buf_arr.tobytes()
            cv2.imshow("Host", cv2_im)
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
        global QUIT
        if QUIT:
            break
    


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
        global QUIT
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


root = Tk.Tk()

# window = Tk.Tk()  #Makes main window
root.wm_title("Video Call Controls")
root.config(background="#FFFFFF")

B_quit = Tk.Button(root, text = 'Quit', command = end_call)
B_quit.grid(row=0, column=0, padx=10, pady=2)

clientVideoSocket = socket(family=AF_INET, type=SOCK_STREAM)
clientVideoSocket.connect((HOST, PORT_VIDEO))
cap = cv2.VideoCapture(0)

clientAudioSocket = socket(family=AF_INET, type=SOCK_STREAM)
clientAudioSocket.connect((HOST, PORT_AUDIO))

audio=pyaudio.PyAudio()
stream=audio.open(format=FORMAT,channels=CHANNELS, rate=RATE, input=True, output = True,frames_per_buffer=CHUNK)

initiation = clientVideoSocket.recv(5).decode()

SendFrameThread = Thread(target=SendFrame)
SendAudioThread = Thread(target=SendAudio)
RecieveFrameThread = Thread(target=RecieveFrame)
RecieveAudioThread = Thread(target=RecieveAudio)

if initiation == "start":
    SendFrameThread.start()
    SendAudioThread.start()
    RecieveFrameThread.start()
    RecieveAudioThread.start()

while CONTINUE:
    root.update()

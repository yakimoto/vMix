import cv2
import numpy as np
import time
import pyfakewebcam
import tkinter as tk
from tkinter import ttk
from threading import Thread
from ndi_find import ndi_find
from ndi_receive import ndi_receive

# set the available resolutions
resolutions = {
    '720p': (1280, 720),
    '1080p': (1920, 1080)
}

# set the default resolution to 720p
default_resolution = '720p'
width, height = resolutions[default_resolution]

# create a window with a dropdown menu to select the NDI source
window = tk.Tk()
window.title('NDI Virtual Webcam')
window.geometry('400x150')
source_label = ttk.Label(window, text='Select NDI source:')
source_label.pack(side=tk.TOP, padx=10, pady=10)
source_var = tk.StringVar(window)
source_var.set('')
source_dropdown = ttk.Combobox(window, textvariable=source_var)
source_dropdown.pack(side=tk.TOP, padx=10, pady=10)

# fill the dropdown menu with available NDI sources
sources = ndi_find()
source_names = [source['name'] for source in sources]
source_dropdown['values'] = source_names
if not sources:
    print("No NDI sources found. Please make sure that an NDI source is running on your network.")


# create a label and dropdown menu to select the webcam device
webcam_label = ttk.Label(window, text='Select Webcam Device:')
webcam_label.pack(side=tk.TOP, padx=10, pady=10)
webcam_var = tk.StringVar(window)
webcam_var.set('')
webcam_dropdown = ttk.Combobox(window, textvariable=webcam_var)
webcam_dropdown.pack(side=tk.TOP, padx=10, pady=10)

# fill the dropdown menu with available webcam devices
webcam_devices = pyfakewebcam.list_devices()
webcam_dropdown['values'] = webcam_devices

# create an NDI receiver object
recv = ndi_receive()

# set the NDI source name to receive from
recv_name = None

# set the frame rate and codec for the video capture
fps = 30
fourcc = cv2.VideoWriter_fourcc(*'H264')

# create a fake webcam object
with pyfakewebcam.FakeWebcam(webcam_devices[0], width, height) as webcam:
    # function to start capturing frames from the NDI stream
    def start_capture():
        global recv_name
        while True:
            if recv_name is None:
                continue
            recv.connect(recv_name)
            frame = recv.recv()
            if frame is None:
                continue
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = np.resize(frame, (width//2, height//2))
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            ret, frame = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            frame = cv2.imdecode(frame, cv2.IMREAD_UNCHANGED)
            webcam.schedule_frame(frame)
            time.sleep(1/fps)

    # function to start the capture thread
def start_capture_thread():
    global recv_name
    recv = ndi_receive()
    recv_name = None
    capture_thread = Thread(target=start_capture)
    capture_thread.daemon = True
    capture_thread.start()


    # continuously update the selected NDI source
    def update_source():
        global recv_name
        recv_name = source_var.get()
        window.after(10, update_source)

    # start updating the selected NDI source
    update_source()

# function to update the selected webcam device
def update_webcam_device():
    global webcam
    device_name = webcam_var.get()
    try:
    webcam = pyfakewebcam.FakeWebcam(device_name, width, height)
except ValueError:
    print(f"Webcam device {device_name} not found. Please select a valid webcam device.")


# create a button to start the capture thread
start_button = ttk.Button(window, text='Start', command=start_capture_thread)
start_button.pack(side=tk.LEFT, padx=10, pady=10)

# create a button to update the webcam device
update_button = ttk.Button(window, text='Update Webcam', command=update_webcam_device)
update_button.pack(side=tk.LEFT, padx=10, pady=10)

# start the main event loop
window.mainloop()

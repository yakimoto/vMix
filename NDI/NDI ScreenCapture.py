import cv2
import pyautogui
import PyNDI as ndi
import numpy as np
import time
import tkinter as tk
from tkinter import ttk

def capture_and_send():
    if not ndi.initialize():
        error_label.config(text="Cannot initialize NDI")
        return

    source_name = "Python NDI Source"
    source = ndi.Source(source_name)

    try:
        sender = ndi.Sender(source, ndi.FOURCC_VIDEO_TYPE_BGRA)
    except Exception as e:
        error_label.config(text=f"Cannot create NDI sender: {str(e)}")
        ndi.finalize()
        return

    fps_option = fps_var.get()
    frame_interval = None if fps_option == "native" else 1.0 / float(fps_option)

    while start_button["state"] == tk.DISABLED:
        try:
            start_time = time.time()

            screenshot = pyautogui.screenshot()
            screenshot = np.array(screenshot)
            screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)

            if flip_var.get():
                screenshot = np.flip(screenshot)

            if rotate_var.get():
                screenshot = np.rot90(screenshot)

            screenshot = cv2.resize(screenshot, (1920, 1080))

            frame = ndi.VideoFrame.from_ndarray(screenshot)
            sender.send_video(frame)

            if frame_interval is not None:
                end_time = time.time()
                elapsed_time = end_time - start_time
                remaining_time = frame_interval - elapsed_time
                if remaining_time > 0:
                    time.sleep(remaining_time)

            if display_position_var.get():
                print(pyautogui.position())

        except Exception as e:
            error_label.config(text=f"Error during capture or send: {str(e)}")
            break

    del sender
    ndi.finalize()

root = tk.Tk()
root.title("NDI Screen Capture")

# FPS Dropdown
fps_label = tk.Label(root, text="FPS:")
fps_label.grid(row=0, column=0, sticky="e", padx=5)

fps_options = ["23.98", "24", "25", "29.97", "30", "50", "59.94", "60", "native"]
fps_var = tk.StringVar(root)
fps_var.set(fps_options[0])  # default value
fps_option_menu = ttk.Combobox(root, textvariable=fps_var, values=fps_options)
fps_option_menu.grid(row=0, column=1, sticky="w")

# Flip Image Checkbox
flip_var = tk.IntVar()
flip_check = tk.Checkbutton(root, text='Flip image', variable=flip_var)
flip_check.grid(row=1, column=0, sticky="e", padx=5)

# Rotate Image Checkbox
rotate_var = tk.IntVar()
rotate_check = tk.Checkbutton(root, text='Rotate image', variable=rotate_var)
rotate_check.grid(row=1, column=1, sticky="w")

# Display Mouse Position Checkbox
display_position_var = tk.IntVar()
display_position_check = tk.Checkbutton(root, text='Display mouse position', variable=display_position_var)
display_position_check.grid(row=2, column=0, sticky="e", padx=5)

# Start and Stop Buttons
start_button = tk.Button(root, text="Start Capture", command=lambda: start_button.config(state=tk.DISABLED) or capture_and_send())
start_button.grid(row=2, column=1, sticky="w", pady=5)

stop_button = tk.Button(root, text="Stop Capture", command=lambda: start_button.config(state=tk.NORMAL))
stop_button.grid(row=2, column=2, sticky="w", pady=5)

# Error message label
error_label = tk.Label(root, text="")
error_label.grid(row=3, column=0, columnspan=3)

root.mainloop()


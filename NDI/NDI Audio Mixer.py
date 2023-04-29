import pyndi
import numpy as np
import sounddevice as sd
from tkinter import *
from tkinter import ttk

# Define the NDI sources to receive
ndi_names = ['NDI Source 1', 'NDI Source 2', 'NDI Source 3']

# Initialize NDI receivers
finder = pyndi.Finder()
sources = finder.get_sources()
ndi_sources = [next((source for source in sources if source.name == name), None) for name in ndi_names]
receivers = [pyndi.Receiver() for _ in ndi_sources]
for receiver, ndi_source in zip(receivers, ndi_sources):
    receiver.create_receiver(ndi_source)

# Initialize Sounddevice output stream
samplerate = receivers[0].audio_sample_rate
blocksize = 1024
channels = receivers[0].audio_channels
output_stream = sd.OutputStream(
    samplerate=samplerate,
    blocksize=blocksize,
    channels=channels,
    dtype='float32'
)

# Start the output stream
output_stream.start()

# Initialize NDI sender
sender = pyndi.Sender()

# Create a new NDI audio source
ndi_name = 'Mixed NDI Audio'
ndi_source = pyndi.AudioSource(name=ndi_name)
sender.create_source(ndi_source)

def change_ndi_name():
    global ndi_name, ndi_source
    new_name = ndi_name_input.get()
    if new_name and new_name != ndi_name:
        ndi_name = new_name
        ndi_source = pyndi.AudioSource(name=ndi_name)
        sender.create_source(ndi_source)

# Initialize dropdown menu to select NDI sources
def update_sources():
    global sources, ndi_sources, receivers
    sources = finder.get_sources()
    ndi_sources = [source for source in sources if source.type == 'audio']
    ndi_names = [source.name for source in ndi_sources]
    receivers = [pyndi.Receiver() for _ in ndi_sources]
    for receiver, ndi_source in zip(receivers, ndi_sources):
        receiver.create_receiver(ndi_source)
    source_menu['menu'].delete(0, 'end')
    for name in ndi_names:
        source_menu['menu'].add_command(label=name, command=lambda ndi_name=name: select_source(ndi_name))
    selected.set(ndi_names[0])
    select_source(ndi_names[0])

def select_source(name):
    global selected_receiver
    ndi_source = next((source for source in ndi_sources if source.name == name), None)
    selected_receiver = next((receiver for receiver in receivers if receiver.source == ndi_source), None)

# Define the volume/fader adjustments for each NDI source
volumes = [0.5, 0.7, 0.9]

# Define the UI
root = Tk()
root.title('NDI Audio Mixer')

frame1 = Frame(root)
frame1.pack(side=TOP)

source_label = Label(frame1, text='Select NDI source:')
source_label.pack(side=LEFT)

selected = StringVar()
source_menu = OptionMenu(frame1, selected, 'Loading...')
source_menu.pack(side=LEFT)

update_sources()

frame2 = Frame(root)
frame2.pack(side=TOP)

volume_sliders = []
for i, ndi_name in enumerate(ndi_names):
    volume_label = Label(frame2, text='Volume for {}:'.format(ndi_name))
    volume_label.grid(row=i, column=0, padx=5, pady=5)
    volume_slider = Scale(frame2, from_=0, to=1, resolution=0.01, orient=HORIZONTAL)
    volume_slider.set(volumes[i])
    volume_slider.grid(row=i, column=1, padx=5, pady=5)
    volume_sliders.append(volume_slider)

frame3 = Frame(root)
frame3.pack(side=TOP)

ndi_name_label = Label(frame3, text='NDI Output Stream Name:')
ndi_name_label.pack(side=LEFT)

ndi_name_input = Entry(frame3)
ndi_name_input.pack(side=LEFT)

change_name_button = Button(frame3, text='Change Name', command=change_ndi_name)
change_name_button.pack(side=LEFT)

# Define the function to mix the audio data from selected NDI sources
def mix_audio(indata, outdata, frames, time, status):
    global selected_receiver, volumes
    if selected_receiver is None:
        outdata.fill(0)
    else:
        mixed_audio = np.zeros_like(outdata)
        for receiver, volume, volume_slider in zip(receivers, volumes, volume_sliders):
            audio_data = receiver.receive_audio(blocksize)
            while len(audio_data) < len(indata):
                audio_data = np.concatenate((audio_data, receiver.receive_audio(blocksize)))
            audio_data = audio_data[:len(indata)]
            mixed_audio += audio_data * volume_slider.get()
        outdata[:] = mixed_audio

# Start the audio stream
with sd.Stream(blocksize=blocksize, callback=mix_audio):
    root.mainloop()

# Stop the output stream
output_stream.stop()

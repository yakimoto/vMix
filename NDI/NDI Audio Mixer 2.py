import pyndi
import numpy as np
import sounddevice as sd
from tkinter import *
from tkinter import ttk

class NDI_Audio_Mixer:
    def __init__(self, ndi_names):
        self.ndi_names = ndi_names
        self.finder = pyndi.Finder()
        self.update_sources()
        self.init_output_stream()
        self.init_ndi_sender()

    def update_sources(self):
        sources = self.finder.get_sources()
        self.ndi_sources = [next((source for source in sources if source.name == name), None) for name in self.ndi_names]
        self.receivers = [pyndi.Receiver() for _ in self.ndi_sources]
        for receiver, ndi_source in zip(self.receivers, self.ndi_sources):
            receiver.create_receiver(ndi_source)

    def init_output_stream(self):
        samplerate = self.receivers[0].audio_sample_rate
        blocksize = 1024
        channels = self.receivers[0].audio_channels
        self.output_stream = sd.OutputStream(
            samplerate=samplerate,
            blocksize=blocksize,
            channels=channels,
            dtype='float32'
        )

    def init_ndi_sender(self):
        self.sender = pyndi.Sender()
        self.ndi_name = 'Mixed NDI Audio'
        self.ndi_source = pyndi.AudioSource(name=self.ndi_name)
        self.sender.create_source(self.ndi_source)

    def change_ndi_name(self, new_name):
        if new_name and new_name != self.ndi_name:
            self.ndi_name = new_name
            self.ndi_source = pyndi.AudioSource(name=self.ndi_name)
            self.sender.create_source(self.ndi_source)

    def mix_audio(self, indata, outdata, frames, time, status, volume_sliders):
        mixed_audio = np.zeros_like(outdata)
        for receiver, volume_slider in zip(self.receivers, volume_sliders):
            audio_data = receiver.receive_audio(frames)
            while len(audio_data) < len(indata):
                audio_data = np.concatenate((audio_data, receiver.receive_audio(frames)))
            audio_data = audio_data[:len(indata)]
            mixed_audio += audio_data * volume_slider.get()
        outdata[:] = mixed_audio

class NDI_Audio_Mixer_UI:
    def __init__(self, mixer):
        self.mixer = mixer
        self.root = Tk()
        self.root.title('NDI Audio Mixer')

        self.init_ui()

    def init_ui(self):
        self.init_frame1()
        self.init_frame2()
        self.init_frame3()

    def init_frame1(self):
        frame1 = Frame(self.root)
        frame1.pack(side=TOP)

        source_label = Label(frame1, text='Select NDI source:')
        source_label.pack(side=LEFT)

        selected = StringVar()
        source_menu = OptionMenu(frame1, selected, 'Loading...')
        source_menu.pack(side=LEFT)

        self.mixer.update_sources()

    def init_frame2(self):
        frame2 = Frame(self.root)
        frame2.pack(side=TOP)

        self.volume_sliders = []
        for i, ndi_name in enumerate(self.mixer.ndi_names):
            volume_label = Label(frame2, text='Volume for {}:'.format(ndi_name))
            volume_label.grid(row=i, column=0, padx=5, pady=5)
            volume_slider = Scale(frame2, from_=0, to=1, resolution=0.01, orient=HORIZONTAL)
            volume_slider.set(0.5)
            volume_slider.grid(row=i, column=1, padx=5, pady=5)
            self.volume_sliders.append(volume_slider)

    def init_frame3(self):
        frame3 = Frame(self.root)
        frame3.pack(side=TOP)

        ndi_name_label = Label(frame3, text='NDI Output Stream Name:')
        ndi_name_label.pack(side=LEFT)

        ndi_name_input = Entry(frame3)
        ndi_name_input.pack(side=LEFT)

        change_name_button = Button(frame3, text='Change Name', command=lambda: self.mixer.change_ndi_name(ndi_name_input.get()))
        change_name_button.pack(side=LEFT)

    def run(self):
        with sd.Stream(blocksize=1024, callback=lambda *args, **kwargs: self.mixer.mix_audio(*args, **kwargs, volume_sliders=self.volume_sliders)):
            self.root.mainloop()

if __name__ == "__main__":
    ndi_names = ['NDI Source 1', 'NDI Source 2', 'NDI Source 3']
    mixer = NDI_Audio_Mixer(ndi_names)
    mixer.output_stream.start()
    ui = NDI_Audio_Mixer_UI(mixer)
    ui.run()
    mixer.output_stream.stop()

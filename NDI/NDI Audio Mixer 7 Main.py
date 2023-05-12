import pyndi
import numpy as np
import sounddevice as sd
import json
import os
import threading
import librosa
import time
from pydub import AudioSegment
from pydub.effects import equalize, compressor
from tkinter import Tk, Frame, Label, Entry, Button, OptionMenu, StringVar, Scale, HORIZONTAL, TOP, LEFT, messagebox
from tkinter import filedialog
from tkinter import Canvas, Checkbutton, IntVar

# Define constants
CONFIG_FILE_NAME = 'ndi_source_config.json'
DEFAULT_NDI_NAMES = ['NDI Source 1', 'NDI Source 2', 'NDI Source 3']

# Configuration class
class Configuration:
    def __init__(self, file_name):
        self.file_name = file_name

    def read(self):
        if os.path.exists(self.file_name):
            with open(self.file_name, 'r') as f:
                config = json.load(f)
        else:
            config = {
                'ndi_sources': DEFAULT_NDI_NAMES
            }
            self.write(config)
        return config

    def write(self, config):
        with open(self.file_name, 'w') as f:
            json.dump(config, f)

    def update_ndi_sources(self, ndi_sources):
        config = self.read()
        config['ndi_sources'] = ndi_sources
        self.write(config)

# Read the configuration file
config = Configuration(CONFIG_FILE_NAME)
configuration_data = config.read()
ndi_names = configuration_data['ndi_sources']

class NDI_Audio_Mixer:
    def __init__(self, ndi_names):
        self.ndi_names = ndi_names
        self.finder = pyndi.Finder()
        self.update_sources()
        self.update_sources_periodically()
        self.init_output_stream()
        self.init_ndi_sender()
        
    def update_sources(self):
        sources = self.finder.get_sources()
        self.ndi_sources = [next((source for source in sources if source.name == name), None) for name in self.ndi_names]
        if None in self.ndi_sources:
            raise ValueError(f"Some NDI sources could not be found: {', '.join(name for name, source in zip(self.ndi_names, self.ndi_sources) if source is None)}")
        self.receivers = [pyndi.Receiver() for _ in self.ndi_sources]
        for receiver, ndi_source in zip(self.receivers, self.ndi_sources):
            receiver.create_receiver(ndi_source)

    def update_sources_periodically(self, interval=5.0):
        self.update_sources()
        threading.Timer(interval, self.update_sources_periodically).start()

    def add_ndi_source(self, name):
        self.ndi_names.append(name)
        self.update_sources()

    def remove_ndi_source(self, name):
        self.ndi_names.remove(name)
        self.update_sources()

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
        # Initialize the NDI sender object with a given name
        self.sender = pyndi.Sender()
        self.ndi_name = 'Mixed NDI Audio'
        self.ndi_source = pyndi.AudioSource(name=self.ndi_name)
        self.sender.create_source(self.ndi_source)

    def change_ndi_name(self, new_name):
        # Change the name of the NDI sender object
        if new_name and new_name != self.ndi_name:
            self.ndi_name = new_name
            self.ndi_source = pyndi.AudioSource(name=self.ndi_name)
            self.sender.create_source(self.ndi_source)

    def apply_eq(self, audio_data, bands, gains):
        audio_segment = AudioSegment(audio_data.tobytes(), frame_rate=self.output_stream.samplerate, channels=self.output_stream.channels, sample_width=audio_data.dtype.itemsize)
        equalized_audio = equalize(audio_segment, bands, gains)
        return np.frombuffer(equalized_audio.raw_data, dtype=audio_data.dtype)

    def apply_compression(self, audio_data, threshold, ratio, attack, release):
        audio_segment = AudioSegment(audio_data.tobytes(), frame_rate=self.output_stream.samplerate, channels=self.output_stream.channels, sample_width=audio_data.dtype.itemsize)
        compressed_audio = compressor(audio_segment, threshold, ratio, attack, release)
        return np.frombuffer(compressed_audio.raw_data, dtype=audio_data.dtype)

    def adjust_phase(self, audio_data, phase_shift):
        # Convert phase shift from degrees to radians
        phase_shift_rad = np.deg2rad(phase_shift)
        complex_audio = librosa.stft(audio_data)
        complex_audio *= np.exp(1j * phase_shift_rad)
        return librosa.istft(complex_audio)
    
    def apply_audio_delay(self, audio_data, delay_ms):
        # Calculate delay in samples
        delay_samples = int(delay_ms * self.output_stream.samplerate / 1000)
        
        # Apply delay by inserting zeros before audio data
        delayed_audio = np.concatenate((np.zeros(delay_samples), audio_data))

        return delayed_audio

    def play_audio_with_delay(volume_slider, mute_button, audio_data, delay_ms):
        if not mute_button.var.get():
            delayed_audio = self.apply_audio_delay(audio_data, delay_ms)
            sd.play(volume_slider.get() * delayed_audio, blocking=False)

    def mix_audio(self, indata, outdata, frames, time, status, volume_sliders, mute_buttons, master_volume_slider, audio_meters, mixed_audio_meter, eq_enabled, compression_enabled, phase_enabled, delay_ms):
        # Mix the audio from different sources and output the mixed audio
        mixed_audio = self.mix_sources(volume_sliders, mute_buttons, frames, delay_ms)
        mixed_audio = self.apply_master_volume(mixed_audio, master_volume_slider.get())
        self.play_audio_with_delay(volume_slider, mute_button, audio_data, delay_ms)


        # Apply the EQ, compression, and phase adjustment if enabled
        if eq_enabled:
            mixed_audio = self.apply_eq(mixed_audio)
        if compression_enabled:
            mixed_audio = self.apply_compression(mixed_audio)
        if phase_enabled:
            mixed_audio = self.adjust_phase(mixed_audio)

        mixed_audio = self.apply_peak_limiter(mixed_audio)  # Apply the peak limiter
        self.update_audio_meters(mixed_audio, audio_meters, mixed_audio_meter)
        outdata[:] = mixed_audio
    
    def mix_sources(self, volume_sliders, mute_buttons, frames, delay_ms):
        # Mix audio sources according to their volume sliders and mute buttons
        mixed_audio = np.zeros(frames)
        for receiver, volume_slider, mute_button in zip(self.receivers, volume_sliders, mute_buttons):
            audio_data = self.receive_audio(receiver, frames)
            delayed_audio = self.apply_audio_delay(audio_data, delay_ms)  # Apply the delay to the audio source
            self.play_audio_with_delay(volume_slider, mute_button, delayed_audio, delay_ms)
            mixed_audio += delayed_audio * volume_slider.get()
        return mixed_audio

    def apply_master_volume(self, mixed_audio, master_volume_slider):
        # Apply the master volume to the mixed audio
        return mixed_audio * master_volume_slider.get()

    def apply_eq(self, mixed_audio):
        # Apply equalization to the mixed audio
        audio_segment = AudioSegment(mixed_audio.tobytes(), frame_rate=self.output_stream.samplerate, channels=self.output_stream.channels, sample_width=mixed_audio.dtype.itemsize)
        equalized_audio = equalize(audio_segment, bands, gains)
        return np.frombuffer(equalized_audio.raw_data, dtype=mixed_audio.dtype)

    def apply_compression(self, mixed_audio):
        # Apply compression to the mixed audio
        audio_segment = AudioSegment(mixed_audio.tobytes(), frame_rate=self.output_stream.samplerate, channels=self.output_stream.channels, sample_width=mixed_audio.dtype.itemsize)
        compressed_audio = compressor(audio_segment, threshold, ratio, attack, release)
        return np.frombuffer(compressed_audio.raw_data, dtype=mixed_audio.dtype)

    def adjust_phase(self, mixed_audio):
        # Apply phase adjustment to the mixed audio
        phase_shift_rad = np.deg2rad(phase_shift)
        complex_audio = librosa.stft(mixed_audio)
        complex_audio *= np.exp(1j * phase_shift_rad)
        return librosa.istft(complex_audio)

    def receive_audio(self, receiver, frames):
        # Receive audio data from the NDI source
        audio_data = receiver.receive_audio(frames)
        while len(audio_data) < frames:
            audio_data = np.concatenate((audio_data, receiver.receive_audio(frames - len(audio_data))))
        return audio_data

    def update_audio_meters(self, mixed_audio, audio_meters, mixed_audio_meter):
        # Update the individual audio meters and the mixed audio meter
        for i, audio_meter in enumerate(audio_meters):
            audio_data = self.receivers[i].receive_audio(len(mixed_audio))
            audio_level = np.average(np.abs(audio_data))
            self.update_audio_meter(audio_meter, audio_level)
        mixed_audio_level = np.average(np.abs(mixed_audio))
        self.update_audio_meter(mixed_audio_meter, mixed_audio_level)

    def update_audio_meter(self, audio_meter, audio_level):
        # Update the audio meter with the current audio level
        audio_meter.delete("all")
        audio_level_db = 20 * np.log10(audio_level)
        audio_level_normalized = np.clip((audio_level_db + 60) / 60, 0, 1)
        audio_meter.create_rectangle(0, 0, 200 * audio_level_normalized, 20, fill="green")

    def apply_peak_limiter(self, mixed_audio, threshold=0.9):
        # Apply a peak limiter to the mixed audio to avoid clipping
        gain_reduction = np.max(np.abs(mixed_audio)) / threshold
        if gain_reduction > 1:
            mixed_audio /= gain_reduction
        return mixed_audio
       
# User interface for the NDI Audio Mixer application
class NDI_Audio_Mixer_UI:
    def __init__(self, ndi_audio_mixer):
        self.ndi_audio_mixer = ndi_audio_mixer
        self.init_ui()

    def init_ui(self):
        self.root = Tk()
        self.root.title('NDI Audio Mixer')
        self.init_main_frame()
        self.init_ndi_sources_frame()
        self.init_mixer_controls_frame()
        self.init_effects_controls_frame()
        self.init_mixed_audio_frame()
        self.init_sender_name_frame()
        self.root.mainloop()

    def init_main_frame(self):
        self.main_frame = Frame(self.root)
        self.main_frame.pack(side=TOP)

    def init_ndi_sources_frame(self):
        self.ndi_sources_frame = Frame(self.main_frame)
        self.ndi_sources_frame.pack(side=LEFT)
        self.init_source_controls()

    def init_source_controls(self):
        self.volume_sliders = []
        self.mute_buttons = []
        self.audio_meters = []

        for i, ndi_name in enumerate(self.ndi_audio_mixer.ndi_names):
            source_frame = Frame(self.ndi_sources_frame)
            source_frame.pack(side=TOP, padx=10, pady=10)

            source_label = Label(source_frame, text=ndi_name)
            source_label.pack(side=TOP)

            volume_slider = Scale(source_frame, from_=0, to=1, resolution=0.01, orient=HORIZONTAL)
            volume_slider.set(1)
            volume_slider.pack(side=TOP)
            self.volume_sliders.append(volume_slider)

            mute_button_var = IntVar()
            mute_button = Checkbutton(source_frame, text="Mute", variable=mute_button_var)
            mute_button.var = mute_button_var
            mute_button.pack(side=TOP)
            self.mute_buttons.append(mute_button)

            audio_meter = Canvas(source_frame, width=200, height=20, bg="white")
            audio_meter.pack(side=TOP)
            self.audio_meters.append(audio_meter)

    def init_mixer_controls_frame(self):
        self.mixer_controls_frame = Frame(self.main_frame)
        self.mixer_controls_frame.pack(side=LEFT, padx=10, pady=10)

        master_volume_label = Label(self.mixer_controls_frame, text="Master Volume")
        master_volume_label.pack(side=TOP)

        self.master_volume_slider = Scale(self.mixer_controls_frame, from_=0, to=1, resolution=0.01, orient=HORIZONTAL)
        self.master_volume_slider.set(1)
        self.master_volume_slider.pack(side=TOP)

        delay_label = Label(self.mixer_controls_frame, text="Delay (ms)")
        delay_label.pack(side=TOP)

        self.delay_slider = Scale(self.mixer_controls_frame, from_=0, to=100, resolution=1, orient=HORIZONTAL)
        self.delay_slider.set(0)
        self.delay_slider.pack(side=TOP)

    def init_mixed_audio_frame(self):
        self.mixed_audio_frame = Frame(self.main_frame)
        self.mixed_audio_frame.pack(side=LEFT, padx=10, pady=10)

        mixed_audio_label = Label(self.mixed_audio_frame, text="Mixed Audio")
        mixed_audio_label.pack(side=TOP)

        self.mixed_audio_meter = Canvas(self.mixed_audio_frame, width=200, height=20, bg="white")
        self.mixed_audio_meter.pack(side=TOP)

    def init_sender_name_frame(self):
        self.sender_name_frame = Frame(self.main_frame)
        self.sender_name_frame.pack(side=LEFT, padx=10, pady=10)

        sender_name_label = Label(self.sender_name_frame, text="NDI Sender Name")
        sender_name_label.pack(side=TOP)

        self.sender_name_entry = Entry(self.sender_name_frame)
        self.sender_name_entry.insert(0, self.ndi_audio_mixer.ndi_name)
        self.sender_name_entry.pack(side=TOP)

        set_sender_name_button = Button(self.sender_name_frame, text="Set", command=self.set_sender_name)
        set_sender_name_button.pack(side=TOP)

    def init_effects_controls_frame(self):
        self.effects_controls_frame = Frame(self.main_frame)
        self.effects_controls_frame.pack(side=LEFT, padx=10, pady=10)

        # EQ controls
        eq_label = Label(self.effects_controls_frame, text="EQ")
        eq_label.pack(side=TOP)

        self.eq_var = IntVar()
        self.eq_checkbutton = Checkbutton(self.effects_controls_frame, text="Enable EQ", variable=self.eq_var)
        self.eq_checkbutton.pack(side=TOP)

        # Compression controls
        compression_label = Label(self.effects_controls_frame, text="Compression")
        compression_label.pack(side=TOP)

        self.compression_var = IntVar()
        self.compression_checkbutton = Checkbutton(self.effects_controls_frame, text="Enable Compression", variable=self.compression_var)
        self.compression_checkbutton.pack(side=TOP)

        # Phase adjustment controls
        phase_label = Label(self.effects_controls_frame, text="Phase Adjustment")
        phase_label.pack(side=TOP)

        self.phase_var = IntVar()
        self.phase_checkbutton = Checkbutton(self.effects_controls_frame, text="Enable Phase Adjustment", variable=self.phase_var)
        self.phase_checkbutton.pack(side=TOP)

    def set_sender_name(self):
        new_name = self.sender_name_entry.get()
        self.ndi_audio_mixer.change_ndi_name(new_name)

        def run(self):
            with self.ndi_audio_mixer.output_stream.callback(
                    lambda indata, outdata, frames, time, status: self.ndi_audio_mixer.mix_audio(
                        indata, outdata, frames, time, status,
                        self.volume_sliders, self.mute_buttons,
                        self.master_volume_slider, self.audio_meters,
                        self.mixed_audio_meter)):
                self.root.mainloop()

# Create the NDI Audio Mixer and user interface
ndi_audio_mixer = NDI_Audio_Mixer(ndi_names)
ndi_audio_mixer_ui = NDI_Audio_Mixer_UI(ndi_audio_mixer)
ndi_audio_mixer_ui.run()
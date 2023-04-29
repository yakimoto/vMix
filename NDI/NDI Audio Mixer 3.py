import pyndi
import numpy as np
import sounddevice as sd
import json
import os
from tkinter import Tk, Frame, Label, Entry, Button, OptionMenu, StringVar, Scale, HORIZONTAL, TOP, LEFT, messagebox
from tkinter import filedialog
from tkinter import Canvas, Checkbutton, IntVar


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

    def update_ndi_source_menu(self):
        self.source_menu["menu"].delete(0, "end")
        for ndi_name in self.mixer.ndi_names:
            self.source_menu["menu"].add_command(label=ndi_name, command=lambda value=ndi_name: self.selected.set(value))
        if self.mixer.ndi_names:
            self.selected.set(self.mixer.ndi_names[0])
        else:
            self.selected.set("No NDI sources found")

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

    def mix_audio(self, indata, outdata, frames, time, status, volume_sliders, mute_buttons, master_volume_slider, audio_meters, mixed_audio_meter):
        mixed_audio = np.zeros_like(outdata)
        indata_len = len(indata)

    for i, (receiver, volume_slider, mute_button) in enumerate(zip(self.receivers, volume_sliders, mute_buttons)):
        if not mute_button.var.get():  # Check if the mute button is not checked
            audio_data = receiver.receive_audio(frames)
            while len(audio_data) < indata_len:
                audio_data = np.concatenate((audio_data, receiver.receive_audio(frames)))
            audio_data = audio_data[:len(indata)]
            mixed_audio += audio_data * volume_slider.get()

            # Calculate audio level and update the audio meter
            audio_level = np.average(np.abs(audio_data))
            audio_meter = audio_meters[i]
            audio_meter.delete("all")
            audio_meter.create_rectangle(0, 0, 200 * audio_level, 20, fill="green")
            
            # Update the mixed audio meter
            mixed_audio_level = np.average(np.abs(mixed_audio))
            mixed_audio_meter.delete("all")
            mixed_audio_meter.create_rectangle(0, 0, 200 * mixed_audio_level, 20, fill="green")


    outdata[:] = mixed_audio * master_volume_slider.get()  # Apply the master volume to the mixed audio

    # Calculate the mixed audio level and update the mixed audio meter
    mixed_audio_level = np.average(np.abs(mixed_audio))
    mixed_audio_meter = Canvas(self.root, width=200, height=20, bg="white")
    mixed_audio_meter.pack(side=TOP)
    mixed_audio_meter.delete("all")
    mixed_audio_meter.create_rectangle(0, 0, 200 * mixed_audio_level, 20, fill="green")



class NDI_Audio_Mixer_UI:
    def __init__(self, mixer):
        self.mixer = mixer
        self.root = Tk()
        self.root.title('NDI Audio Mixer')

        self.init_ui()

    def init_ui(self):
        self.selected = StringVar()
        self.source_menu = OptionMenu(self.root, self.selected, 'Loading...')
        self.init_frame1()
        self.init_frame2()
        self.init_frame3()
        self.init_frame4()
        self.init_frame5()
        self.init_mixed_audio_meter()


    def init_frame1(self):
        frame1 = Frame(self.root)
        frame1.pack(side=TOP)

        source_label = Label(frame1, text='Select NDI source:')
        source_label.pack(side=LEFT)

        selected = self.selected
        source_menu = self.source_menu

        self.mixer.update_sources()
        self.update_ndi_source_menu()

    def update_ndi_source_menu(self):
        self.source_menu["menu"].delete(0, "end")
        for ndi_name in self.mixer.ndi_names:
            self.source_menu["menu"].add_command(label=ndi_name, command=lambda value=ndi_name: self.selected.set(value))
        if self.mixer.ndi_names:
            self.selected.set(self.mixer.ndi_names[0])
        else:
            self.selected.set("No NDI sources found")

        

    def update_sources_periodically(self):
        try:
            self.mixer.update_sources()
            self.update_ndi_source_menu()
        except Exception as e:
            messagebox.showerror('Error', f'Error refreshing NDI sources: {e}')
        self.root.after(5000, self.update_sources_periodically)  # Check for new sources every 5 seconds




    def init_frame2(self):
        frame2 = Frame(self.root)
        frame2.pack(side=TOP)

        self.volume_sliders = []
        self.mute_buttons = []  # Add a list to keep track of mute buttons
        self.audio_meters = []  # Add a list to keep track of audio meters

        for i, ndi_name in enumerate(self.mixer.ndi_names):
            volume_label = Label(frame2, text=f'Volume for {ndi_name}:')
            volume_label.grid(row=i, column=0, padx=5, pady=5)
            volume_slider = Scale(frame2, from_=0, to=1, resolution=0.01, orient=HORIZONTAL)
            volume_slider.set(0.5)
            volume_slider.grid(row=i, column=1, padx=5, pady=5)
            self.volume_sliders.append(volume_slider)

            mute_var = IntVar()
            mute_button = Checkbutton(frame2, text="Mute", variable=mute_var)
            mute_button.var = mute_var
            mute_button.grid(row=i, column=2, padx=5, pady=5)
            self.mute_buttons.append(mute_button)  # Store the mute button in the list

            audio_meter = Canvas(frame2, width=200, height=20, bg="white")
            audio_meter.grid(row=i, column=3, padx=5, pady=5)
            self.audio_meters.append(audio_meter)  # Store the audio meter in the list



    def init_frame3(self):
        frame3 = Frame(self.root)
        frame3.pack(side=TOP)

        ndi_name_label = Label(frame3, text='NDI Output Stream Name:')
        ndi_name_label.pack(side=LEFT)

        ndi_name_input = Entry(frame3)
        ndi_name_input.pack(side=LEFT)

        change_name_button = Button(frame3, text='Change Name', command=lambda: self.mixer.change_ndi_name(ndi_name_input.get()))
        change_name_button.pack(side=LEFT)

        
    def init_frame4(self):
        frame4 = Frame(self.root)
        frame4.pack(side=TOP)

        save_button = Button(frame4, text='Save Configuration', command=self.save_configuration)
        save_button.pack(side=LEFT)

        load_button = Button(frame4, text='Load Configuration', command=self.load_configuration)
        load_button.pack(side=LEFT)

        refresh_button = Button(frame4, text='Refresh NDI Sources', command=self.refresh_ndi_sources)
        refresh_button.pack(side=LEFT)

    def init_frame5(self):
        frame5 = Frame(self.root)
        frame5.pack(side=TOP)

        master_volume_label = Label(frame5, text='Master Volume:')
        master_volume_label.pack(side=LEFT)

        self.master_volume_slider = Scale(frame5, from_=0, to=1, resolution=0.01, orient=HORIZONTAL)
        self.master_volume_slider.set(1)
        self.master_volume_slider.pack(side=LEFT)

    def init_mixed_audio_meter(self):
        mixed_audio_meter = Canvas(self.root, width=200, height=20, bg="white")
        mixed_audio_meter.pack(side=TOP)
        self.mixed_audio_meter = mixed_audio_meter




    def refresh_ndi_sources(self):
        try:
            self.mixer.update_sources()
            self.update_ndi_source_menu()
        except Exception as e:
            messagebox.showerror('Error', f'Error refreshing NDI sources: {e}')

    def save_configuration(self):
        file_path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON files', '*.json'), ('All files', '*.*')])
        if file_path:
            config = {
                'ndi_output_stream_name': self.mixer.ndi_name,
                'volume_settings': [slider.get() for slider in self.volume_sliders]
            }
            try:
                with open(file_path, 'w') as f:
                    json.dump(config, f)
                messagebox.showinfo('Success', 'Configuration saved successfully.')
            except Exception as e:
                messagebox.showerror('Error', f'Error saving configuration: {e}')

    def load_configuration(self):
        file_path = filedialog.askopenfilename(defaultextension='.json', filetypes=[('JSON files', '*.json'), ('All files', '*.*')])
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    config = json.load(f)
                self.mixer.change_ndi_name(config['ndi_output_stream_name'])
                for slider, volume in zip(self.volume_sliders, config['volume_settings']):
                    slider.set(volume)
                messagebox.showinfo('Success', 'Configuration loaded successfully.')
            except Exception as e:
                messagebox.showerror('Error', f'Error loading configuration: {e}')

    def run(self):
        try:
            with sd.Stream(blocksize=1024, callback=lambda *args, **kwargs: self.mixer.mix_audio(*args, **kwargs, volume_sliders=self.volume_sliders, mute_buttons=self.mute_buttons, master_volume_slider=self.master_volume_slider, audio_meters=self.audio_meters, mixed_audio_meter=self.mixed_audio_meter)):
                self.root.mainloop()
        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.mixer.output_stream.stop()


if __name__ == "__main__":
    ndi_names = ['NDI Source 1', 'NDI Source 2', 'NDI Source 3']
    mixer = NDI_Audio_Mixer(ndi_names)
    mixer.output_stream.start()
    ui = NDI_Audio_Mixer_UI(mixer)
    ui.run()
    mixer.output_stream.stop()

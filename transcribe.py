import tkinter as tk
from tkinter import scrolledtext
import threading
import sounddevice as sd
import numpy as np
import wave
import tempfile
import pyperclip
import whisper
import openai
from dotenv import load_dotenv
import os
import customtkinter as ctk

# Set appearance mode and default color theme
ctk.set_appearance_mode("dark")  # Modes: "dark", "light"
ctk.set_default_color_theme("blue")  # Themes: "blue", "green", "dark-blue"

# Dark green accent color
ACCENT_COLOR = "#2e8b57"  # Sea green

# Load environment variables
load_dotenv('/home/km/Software/transcribe/.env')  # Adjust path as needed

# Set up OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("No OpenAI API key found. Please check your .env file.")

# Global variables for audio recording
audio_frames = []    # List to store recorded audio chunks
stream = None        # The sounddevice stream
is_recording = False # Flag to indicate if we are actively recording

# Global variable to store the chosen device (default to None)
selected_input_device = None

# Audio configuration: Adjusted for Whisper's optimal performance
RATE = 16000          # Changed from 48000 to 16000 for Whisper
CHANNELS = 1
CHUNK_SIZE = 4096     # Increased from 1024 to 4096 to reduce overflow warnings
DEVICE_TIMEOUT = 1.0   # Device timeout in seconds

def audio_callback(indata, frames, time, status):
    """This callback is called for each audio block from the microphone."""
    global audio_frames
    if status:
        # Print overflow warnings (or other statuses) if they occur.
        # Overflows are common if the callback is not fast enough.
        if 'overflow' in str(status):
            print(f"Audio callback warning: {status}")
        else:
            print(f"Audio Callback Status: {status}")
    
    try:
        # Only append if we're recording and the block has data.
        if is_recording and indata.size > 0:
            audio_frames.append(indata.copy())
            # Prevent memory overflow by limiting total recording time (300 seconds max)
            if len(audio_frames) > (RATE * 300) // CHUNK_SIZE:
                stop_recording()
                status_label.configure(text="Recording stopped - maximum length reached")
    except Exception as e:
        print(f"Error in audio callback: {e}")

def list_audio_devices():
    """List all available audio input devices and their properties."""
    devices = sd.query_devices()
    input_devices = []
    print("\nDetailed Audio Device List:")
    print("-" * 50)
    
    for i, device in enumerate(devices):
        try:
            detailed_info = sd.query_devices(device=i)
            if detailed_info['max_input_channels'] > 0:
                print(f"\nDevice ID: [{i}] {detailed_info['name']}")
                print(f"    API: {detailed_info['hostapi']}")
                print(f"    Input channels: {detailed_info['max_input_channels']}")
                print(f"    Sample Rate: {detailed_info['default_samplerate']}Hz")
                print(f"    Is Default Device: {'*' if detailed_info.get('default_input') else ''}")
                input_devices.append(i)
        except Exception as e:
            print(f"Error querying device {i}: {e}")
    
    if not input_devices:
        print("\nNo input devices found! Please check your microphone connection.")
    
    return devices

def create_device_selection_dialog():
    """Create a GUI dialog for device selection."""
    global selected_input_device, RATE
    dialog = ctk.CTkToplevel(root)
    dialog.title("Select Audio Input Device")
    dialog.geometry("450x500")  # Smaller dialog size
    
    # Temporarily withdraw the window to prevent flashing
    dialog.withdraw()
    
    frame = ctk.CTkFrame(dialog)
    frame.pack(fill="both", expand=True, padx=15, pady=15)  # Reduced padding
    
    title_label = ctk.CTkLabel(frame, text="Select Audio Device", 
                              font=ctk.CTkFont(size=18, weight="bold"),  # Smaller font
                              text_color=ACCENT_COLOR)  # Using accent color
    title_label.pack(pady=(0, 15))  # Reduced padding
    
    info_text = ctk.CTkTextbox(frame, height=250, width=420)  # Smaller textbox
    info_text.pack(pady=8)  # Reduced padding
    
    selected_device_str = ctk.StringVar(dialog)
    
    def test_device():
        global selected_input_device
        try:
            device_id = int(selected_device_str.get().split()[0])
            device_info = sd.query_devices(device=device_id)
            
            # We'll keep RATE at 16000 for Whisper compatibility regardless of device
            # but we'll make sure the device supports it
            if device_info['default_samplerate'] < 16000:
                info_text.delete("0.0", "end")
                info_text.insert("0.0", f"Warning: Device {device_info['name']} has a sample rate of {device_info['default_samplerate']}Hz, which is below the recommended 16000Hz for Whisper.")
                return
            
            # Update the default device (input only)
            current_default = sd.default.device
            if current_default is None or not isinstance(current_default, (list, tuple)):
                current_default = (None, None)
            sd.default.device = (device_id, current_default[1])
            selected_input_device = device_id  # Store the selected device
            
            info_text.delete("0.0", "end")
            info_text.insert("0.0", f"Testing device: {device_info['name']}\n")
            info_text.insert("end", "Recording for 3 seconds...\n")
            info_text.insert("end", "Please speak into the microphone...\n")
            dialog.update()
            
            duration = 3
            recording = sd.rec(int(duration * RATE), samplerate=RATE, channels=1, dtype='float32', device=device_id)
            sd.wait()
            
            max_level = np.max(np.abs(recording))
            info_text.insert("end", f"\nMaximum audio level: {max_level:.4f}\n")
            
            if max_level > 0.01:
                info_text.insert("end", "✓ Audio input detected!\n")
                if max_level > 0.8:
                    info_text.insert("end", "Note: Audio levels very high\n")
                elif max_level < 0.1:
                    info_text.insert("end", "Note: Audio levels quite low\n")
            else:
                info_text.insert("end", "✗ No audio detected. Please check:\n")
                info_text.insert("end", "  - Microphone is not muted\n")
                info_text.insert("end", "  - System input volume\n")
                info_text.insert("end", "  - Microphone permissions\n")
            
        except Exception as e:
            info_text.delete("0.0", "end")
            info_text.insert("0.0", f"Error testing device: {str(e)}")
    
    def select_and_close():
        global selected_input_device
        try:
            if selected_device_str.get():
                device_id = int(selected_device_str.get().split()[0])
                current_default = sd.default.device
                if current_default is None or not isinstance(current_default, (list, tuple)):
                    current_default = (None, None)
                sd.default.device = (device_id, current_default[1])
                selected_input_device = device_id  # Store the selected device
                status_label.configure(text=f"Selected: {sd.query_devices(device=device_id)['name']}")
                dialog.destroy()
        except Exception as e:
            info_text.delete("0.0", "end")
            info_text.insert("0.0", f"Error setting device: {str(e)}")
    
    devices = sd.query_devices()
    device_list = []
    
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            device_str = f"{i} - {device['name']} ({device['max_input_channels']} channels)"
            device_list.append(device_str)
    
    if device_list:
        device_selector_label = ctk.CTkLabel(frame, text="Audio Input Device:", 
                                           font=ctk.CTkFont(size=12))  # Smaller font
        device_selector_label.pack(pady=(15, 5), anchor="w")  # Adjusted padding
        
        device_menu = ctk.CTkOptionMenu(frame, variable=selected_device_str, values=device_list, 
                                      width=360,  # Smaller width
                                      fg_color="#444444",
                                      button_color=ACCENT_COLOR,  # Using accent color
                                      button_hover_color="#1c6e3d")  # Darker accent for hover
        device_menu.pack(pady=5)
        selected_device_str.set(device_list[0])
        
        button_frame = ctk.CTkFrame(frame, fg_color="transparent")
        button_frame.pack(pady=15, fill="x")  # Reduced padding
        
        test_button = ctk.CTkButton(button_frame, text="Test Device", command=test_device, 
                                  width=150, # Smaller width
                                  fg_color="#444444", 
                                  hover_color=ACCENT_COLOR,  # Using accent color for hover
                                  height=30,  # Smaller height
                                  corner_radius=4)
        test_button.pack(side="left", padx=8)  # Reduced padding
        
        select_button = ctk.CTkButton(button_frame, text="Select Device", command=select_and_close, 
                                    width=150,  # Smaller width
                                    fg_color="#444444", 
                                    hover_color=ACCENT_COLOR,  # Using accent color for hover
                                    height=30,  # Smaller height
                                    corner_radius=4)
        select_button.pack(side="right", padx=8)  # Reduced padding
        
        info_text.insert("0.0", "Available Input Devices:\n\n")
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                info_text.insert("end", f"Device ID: [{i}] {device['name']}\n")
                info_text.insert("end", f"    Channels: {device['max_input_channels']}\n")
                info_text.insert("end", f"    Sample Rate: {device['default_samplerate']}Hz\n")
                info_text.insert("end", f"    Default: {'Yes' if device.get('default_input') else 'No'}\n\n")
    else:
        info_text.insert("0.0", "No input devices found!\n")
        info_text.insert("end", "Please check your microphone connection.")
    
    # Position the window relative to the parent
    dialog.update_idletasks()  # Make sure window size is updated
    
    # Get the window size
    dialog_width = dialog.winfo_width()
    dialog_height = dialog.winfo_height()
    
    # Get the parent window position
    parent_x = root.winfo_x()
    parent_y = root.winfo_y()
    parent_width = root.winfo_width()
    parent_height = root.winfo_height()
    
    # Calculate position
    x_pos = parent_x + (parent_width - dialog_width) // 2
    y_pos = parent_y + (parent_height - dialog_height) // 2
    
    # Set the position and make the window visible
    dialog.geometry(f"+{x_pos}+{y_pos}")
    dialog.deiconify()  # Make the window visible
    
    # Now it's safe to grab, as the window is visible
    dialog.focus_set()
    dialog.grab_set()
    dialog.wait_window()

def add_device_selection_button(control_frame):
    device_button = ctk.CTkButton(
        control_frame,
        text="Select Device",
        command=create_device_selection_dialog,
        fg_color="#555555",
        hover_color="#777777",
        width=120,
        height=35,
        corner_radius=4
    )
    device_button.pack(side="right", padx=10)

def start_recording():
    """Start (or resume) audio recording."""
    global stream, is_recording, audio_frames, selected_input_device, RATE
    if not is_recording:
        try:
            audio_frames = []
            # Determine the input device ID:
            if selected_input_device is not None:
                device_id = selected_input_device
            elif (sd.default.device is not None and isinstance(sd.default.device, (list, tuple)) 
                  and sd.default.device[0] is not None):
                device_id = sd.default.device[0]
            else:
                # Get the first available input device
                devices = sd.query_devices()
                device_id = None
                
                # First try to find the HD Pro Webcam C920 if available
                for i, device in enumerate(devices):
                    if device['max_input_channels'] > 0 and 'HD Pro Webcam C920' in device['name']:
                        device_id = i
                        print(f"Found and using HD Pro Webcam C920 as device {i}")
                        break
                
                # If webcam not found, use any available input device
                if device_id is None:
                    for i, device in enumerate(devices):
                        if device['max_input_channels'] > 0:
                            device_id = i
                            break
                
                if device_id is None:
                    raise ValueError("No input devices found")
            
            # Get device info
            device_info = sd.query_devices(device=device_id)
            
            # Always use 16000Hz for Whisper, resampling if needed
            supported_rate = 16000
            
            print(f"\nStarting recording with device: {device_info['name']}")
            print(f"Sample rate: {supported_rate}Hz (fixed for Whisper)")
            print(f"Channels: {CHANNELS}")
            
            # Create and start the stream
            stream = sd.InputStream(
                samplerate=supported_rate,
                channels=CHANNELS,
                callback=audio_callback,
                device=device_id,
                dtype='float32',
                blocksize=CHUNK_SIZE,
                latency='high'  # Changed from 'low' to 'high' to reduce overflow errors
            )
            
            stream.start()
            is_recording = True
            
            # Update UI elements to reflect recording state
            start_button.configure(state="disabled")
            pause_button.configure(state="normal")
            stop_button.configure(state="normal")
            
            # Animate the recording indicator
            update_recording_indicator()
            
            status_label.configure(text=f"Recording... (Using {device_info['name']})")
            
        except Exception as e:
            error_msg = f"Recording error: {str(e)}"
            status_label.configure(text=error_msg)
            print(f"Detailed error: {e.__class__.__name__}: {str(e)}")
            # Reset the stream if there was an error
            if stream is not None:
                try:
                    stream.close()
                except:
                    pass
                stream = None
            is_recording = False

def update_recording_indicator():
    """Update the recording indicator animation"""
    global is_recording
    if is_recording:
        # Update the text indicator 
        current_text = status_label.cget("text")
        if current_text.endswith("..."):
            new_text = current_text.replace("...", "")
        else:
            new_text = current_text + "."
        status_label.configure(text=new_text)
        
        # Flash the recording indicator between accent color and dark variant
        current_color = recording_indicator.cget("text_color")
        if current_color == ACCENT_COLOR:  # Accent color
            recording_indicator.configure(text_color="#1c6e3d")  # Dark accent
        else:
            recording_indicator.configure(text_color=ACCENT_COLOR)  # Accent color
            
        root.after(500, update_recording_indicator)
    else:
        # Reset indicator to gray when not recording
        recording_indicator.configure(text_color="#333333")

def pause_recording():
    """Pause the current recording session."""
    global stream, is_recording
    if is_recording and stream is not None:
        stream.stop()
        stream.close()
        stream = None
        is_recording = False
        status_label.configure(text="Paused")
        
        # Update button states
        start_button.configure(state="normal")
        pause_button.configure(state="disabled")
        
        # Reset recording indicator
        recording_indicator.configure(text_color="#333333")

def stop_recording():
    """Stop recording and start processing the recorded audio."""
    global stream, is_recording
    if is_recording and stream is not None:
        try:
            is_recording = False
            stream.stop()
            stream.close()
            stream = None
            status_label.configure(text="Processing transcription...")
            
            # Update button states 
            start_button.configure(state="normal")
            pause_button.configure(state="disabled")
            stop_button.configure(state="disabled")
            
            # Reset recording indicator
            recording_indicator.configure(text_color="#333333")
            
            # Show a progress indicator in the text area
            text_box.delete("0.0", "end")
            text_box.insert("0.0", "Transcribing audio...\nThis may take a moment.")
            
            threading.Thread(target=process_audio, daemon=True).start()
        except Exception as e:
            print(f"Error stopping recording: {e}")

def process_audio():
    """Process the recorded audio: write to WAV, transcribe with Whisper, and update the GUI."""
    global audio_frames
    wav_path = None
    
    try:
        if not audio_frames or len(audio_frames) == 0:
            transcription = "No audio recorded."
            status_label.configure(text="No audio recorded.")
            stop_button.configure(state="normal")
            return

        print(f"Processing {len(audio_frames)} audio chunks...")
        audio_data = np.concatenate(audio_frames, axis=0)
        print(f"Combined audio shape: {audio_data.shape}")
        
        audio_max = np.max(np.abs(audio_data))
        print(f"Maximum audio level: {audio_max}")
        
        if audio_max < 0.01:
            transcription = "Audio level too low - please check microphone"
            status_label.configure(text="Audio level too low")
            stop_button.configure(state="normal")
            return

        audio_data_int16 = np.int16(audio_data * 32767)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
            wav_path = tmpfile.name
            with wave.open(wav_path, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(2)
                wf.setframerate(RATE)  # Use the fixed RATE of 16000Hz
                wf.writeframes(audio_data_int16.tobytes())

        print(f"Audio saved to: {wav_path}")
        print("Loading Whisper model...")
        
        model = whisper.load_model("base")
        result = model.transcribe(wav_path)
        transcription = result.get("text", "").strip()
        
        if not transcription:
            transcription = "No speech detected in the audio."

    except Exception as e:
        print(f"Error during transcription: {str(e)}")
        transcription = f"Error during transcription: {str(e)}"
        
    finally:
        if wav_path and os.path.exists(wav_path):
            try:
                os.unlink(wav_path)
            except Exception as e:
                print(f"Error deleting temporary file: {str(e)}")
        
        audio_frames = []
        root.after(0, update_gui, transcription)
        stop_button.configure(state="normal")

def update_gui(transcription):
    """Update the text widget with the transcription and copy the text to the clipboard."""
    text_box.delete("0.0", "end")
    text_box.insert("0.0", transcription)
    pyperclip.copy(transcription)
    status_label.configure(text="✓ Transcription complete. Text copied to clipboard.")

# --------------------- GUI Setup --------------------- #
root = ctk.CTk()
root.title("Voice to Text Transcriber")
root.geometry("700x500")  # Reduced from 800x600
root.minsize(600, 400)    # Reduced minimum size

main_frame = ctk.CTkFrame(root)
main_frame.pack(fill="both", expand=True, padx=15, pady=15)  # Reduced padding

# Title area
title_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
title_frame.pack(fill="x", pady=(0, 15))  # Reduced padding

title_label = ctk.CTkLabel(
    title_frame, 
    text="Voice to Text Transcriber", 
    font=ctk.CTkFont(size=20, weight="bold"),  # Smaller font
    text_color=ACCENT_COLOR  # Using accent color
)
title_label.pack(side="left")

# Recording indicator
recording_indicator = ctk.CTkLabel(
    title_frame,
    text="●",
    font=ctk.CTkFont(size=20),  # Smaller font
    text_color="#333333"  # Start with gray (inactive)
)
recording_indicator.pack(side="right")

# Control buttons area
control_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
control_frame.pack(fill="x", pady=8)  # Reduced padding

button_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
button_frame.pack(side="left")

# Create custom recording control buttons with icons
start_button = ctk.CTkButton(
    button_frame, 
    text="Record", 
    command=start_recording,
    fg_color="#444444",
    hover_color=ACCENT_COLOR,  # Using accent color for hover
    width=100,  # Smaller width
    height=30,  # Smaller height
    corner_radius=4
)
start_button.pack(side="left", padx=8)  # Reduced padding

pause_button = ctk.CTkButton(
    button_frame, 
    text="Pause", 
    command=pause_recording,
    fg_color="#444444",
    hover_color=ACCENT_COLOR,  # Using accent color for hover
    width=100,  # Smaller width
    height=30,  # Smaller height
    corner_radius=4,
    state="disabled"
)
pause_button.pack(side="left", padx=8)  # Reduced padding

stop_button = ctk.CTkButton(
    button_frame, 
    text="Stop", 
    command=stop_recording,
    fg_color="#444444",
    hover_color=ACCENT_COLOR,  # Using accent color for hover
    width=100,  # Smaller width
    height=30,  # Smaller height
    corner_radius=4,
    state="disabled"
)
stop_button.pack(side="left", padx=8)  # Reduced padding

def add_device_selection_button(control_frame):
    device_button = ctk.CTkButton(
        control_frame,
        text="Select Device",
        command=create_device_selection_dialog,
        fg_color="#444444",
        hover_color=ACCENT_COLOR,  # Using accent color for hover
        width=100,  # Smaller width
        height=30,  # Smaller height
        corner_radius=4
    )
    device_button.pack(side="right", padx=8)  # Reduced padding

add_device_selection_button(control_frame)

# Status area
status_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
status_frame.pack(fill="x", pady=6)  # Reduced padding

status_label = ctk.CTkLabel(
    status_frame, 
    text="Ready - Press 'Record' to start",
    font=ctk.CTkFont(size=12),  # Smaller font
    text_color="#aaaaaa"
)
status_label.pack(anchor="w")

# Text display area
text_frame = ctk.CTkFrame(main_frame)
text_frame.pack(fill="both", expand=True, pady=8)  # Reduced padding

text_box = ctk.CTkTextbox(
    text_frame, 
    wrap="word",
    font=ctk.CTkFont(size=14),  # Smaller font
    corner_radius=4,  # Smaller corner radius
    border_width=1,
    border_color=ACCENT_COLOR,  # Using accent color for border
)
text_box.pack(fill="both", expand=True, padx=8, pady=8)  # Reduced padding

# Footer with instructions
footer_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
footer_frame.pack(fill="x", pady=(8, 0))  # Reduced padding

footer_label = ctk.CTkLabel(
    footer_frame,
    text="Transcription automatically copied to clipboard",  # Shortened text
    font=ctk.CTkFont(size=10),  # Smaller font
    text_color="#888888"
)
footer_label.pack(side="right")

# List available devices on startup (printed to console)
list_audio_devices()

if __name__ == "__main__":
    root.mainloop()

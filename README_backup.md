# Voice to Text Transcriber

A modern desktop application for real-time voice-to-text transcription using OpenAI's Whisper model. Features a clean dark-themed GUI built with CustomTkinter.

## Features

- **Real-time audio recording** with visual feedback
- **Local transcription** using OpenAI Whisper (no internet required for transcription)
- **Audio device selection** with testing capabilities
- **Automatic clipboard copying** of transcribed text
- **Modern dark UI** with customizable themes
- **Pause/Resume recording** functionality
- **Audio level monitoring** and device compatibility checking

## Requirements

### System Requirements
- Python 3.7 or higher
- Linux/Windows/macOS
- Microphone or audio input device
- At least 1GB RAM (for Whisper model)

### Python Dependencies
```
tkinter (usually included with Python)
sounddevice
numpy
wave
tempfile
pyperclip
whisper
openai
python-dotenv
customtkinter
```

## Installation

1. **Clone or download** the project files to your desired directory

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create environment file** for API key:
   ```bash
   # In your project directory, create a file named .env
   touch .env
   ```

4. **Add your OpenAI API key** to the `.env` file:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

## API Key Setup

### Getting an OpenAI API Key

1. Go to [OpenAI's website](https://openai.com/)
2. Sign up for an account or log in
3. Navigate to the [API Keys page](https://platform.openai.com/api-keys)
4. Click "Create new secret key"
5. Copy the generated key

### Setting Up the .env File

Create a `.env` file in the same directory as `transcribe.py`:

```bash
# .env file content
OPENAI_API_KEY=sk-your-actual-api-key-here
```

**Important Notes:**
- Replace `sk-your-actual-api-key-here` with your actual OpenAI API key
- Keep your API key secure and never share it publicly
- The .env file should be in the same directory as transcribe.py
- Update the path in the code if your .env file is in a different location

## Usage

1. **Run the application:**
   ```bash
   python transcribe.py
   ```

2. **Select your audio device:**
   - Click "Select Device" button
   - Choose your microphone from the list
   - Click "Test Device" to verify it's working
   - Click "Select Device" to confirm

3. **Record and transcribe:**
   - Click "Record" to start recording
   - Speak into your microphone
   - Click "Pause" to pause recording (optional)
   - Click "Stop" to end recording and start transcription
   - The transcribed text will appear in the text box and be copied to your clipboard

## Audio Settings

The application is optimized for Whisper with these settings:
- **Sample Rate:** 16,000 Hz (optimal for Whisper)
- **Channels:** 1 (mono)
- **Chunk Size:** 4,096 samples
- **Maximum Recording:** 5 minutes (300 seconds)

## Troubleshooting

### Common Issues

**"No input devices found"**
- Check that your microphone is connected and recognized by your system
- Try running the device selection dialog to see available devices
- Ensure your system has proper audio drivers installed

**"Audio level too low"**
- Check your microphone volume settings
- Ensure the microphone is not muted
- Try speaking closer to the microphone
- Test with the "Test Device" feature

**"Recording error" or overflow warnings**
- Try selecting a different audio device
- Close other applications that might be using the microphone
- Restart the application

**"No OpenAI API key found"**
- Ensure your .env file is in the correct location
- Check that the API key is formatted correctly in the .env file
- Verify the .env file is named correctly (not .env.txt)

### Audio Device Issues

If you're having trouble with audio devices:

1. **List available devices** by checking the console output when starting the application
2. **Try different devices** if you have multiple input options
3. **Check system audio settings** to ensure the device is enabled
4. **Restart the application** after changing system audio settings

### Performance Tips

- **Close other audio applications** while using the transcriber
- **Use a good quality microphone** for better transcription accuracy
- **Speak clearly** and at a moderate pace
- **Minimize background noise** for better results

## File Structure

```
transcribe/
├── transcribe.py          # Main application file
├── .env                   # Environment variables (API key)
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Technical Details

- **GUI Framework:** CustomTkinter with dark theme
- **Audio Processing:** sounddevice for real-time audio capture
- **Transcription:** OpenAI Whisper (local processing)
- **Audio Format:** 16-bit PCM WAV files
- **Temporary Files:** Automatically cleaned up after processing

## License

This project is open source. Please ensure you comply with OpenAI's usage policies when using their API.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify all dependencies are installed correctly
3. Ensure your .env file is properly configured
4. Check console output for detailed error messages 
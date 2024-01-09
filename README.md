## Transcribe Video with Whisper
This app uses Azure OpenAI Whisper to transcribe a YouTube video. You'll need to have a Deployment of Whisper, which is currently available in the *North Central* Azure Region.

## Prerequisites
- An Azure Subscription
- A Deployment of Whisper (at time of writing, available in the *North Central* Azure Region)
- Python 3.11 or higher

## Setup
1. Clone this repo
2. Create a virtual environment
3. Install the requirements
4. Use .env.example to create a .env file in the root of the project
5. Run the app
   
In this example, the following YouTube URL is downloaded, split into 2 audio files, and transcribed:
```
python app.py https://www.youtube.com/watch?v=dQw4w9WgXcQ 2
```

## Notes
Parameters: <YouTube URL> [<num_splits>] [<output_file>] [<transcription_file>]

Here:
- YouTube URL: The URL of the YouTube video to download and transcribe
- num_splits: The number of audio files to split the video into. Defaults to 10
- output_file: The name of the output file. Defaults to the code of the YouTube video (e.g. dQw4w9WgXcQ in the example above)
- transcription_file: The name of the transcription file. Defaults to the output_file with a .txt extension (e.g. dQw4w9WgXcQ.txt in the example above)
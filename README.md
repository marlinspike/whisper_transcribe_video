## Transcribe Video with Whisper
This app uses Azure OpenAI Whisper to transcribe a YouTube video, or a local Audio/Video file. You'll need to have a Deployment of Whisper in Azure, which is currently available in the *North Central* Azure Region.

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
Parameters: <YouTube_URL OR Audio/Video_File> [<num_splits>] [<output_file>] [<transcription_file>]


Here:
- YouTube_URL or Audio/Video_File: The URL or Path of the YouTube video or local Audio/Video file to transcribe. If a YouTube URL is provided, it's first downloaded and then split/transcribed. If a local Audio/Video file is provided, it's split/transcribed.
- num_splits: The number of audio files to split the video into. Defaults to 5
- output_file: The name of the output file. Defaults to the code of the YouTube video (e.g. dQw4w9WgXcQ in the example above)
- transcription_file: The name of the transcription file. Defaults to the output_file with a .txt extension (e.g. dQw4w9WgXcQ.txt in the example above)

You can use the *batch_processor.py* app and the *youtube_vodeos.csv* file to process a batch of YouTube videos. The *youtube_videos.csv* file contains a list of YouTube videos to process, and the *batch_processor.py* app will process each video in the list.

## License
MIT
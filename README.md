## Transcribe Video with Whisper

This app uses Azure OpenAI Whisper to transcribe a YouTube video or a local Audio/Video file. You'll need to have a Deployment of Whisper in Azure, which is currently available in the *North Central* Azure Region.

## Prerequisites

- An Azure Subscription
- A Deployment of Whisper (at the time of writing, available in the *North Central* Azure Region)
- Python 3.11 or higher

## Setup

1. Clone this repo
2. Install *ffmpeg*. If you're on a Mac, you can just `brew install ffmpeg`
3. Create a virtual environment
4. Install the requirements
5. Use .env.example to create a .env file in the root of the project
6. Run the app

In this example, the following YouTube URL is downloaded, split into 2 audio files, and transcribed:
python app.py https://www.youtube.com/watch?v=dQw4w9WgXcQ 2

## Notes

Parameters: <YouTube_URL OR Audio/Video_File> [<num_splits>] [<output_file>] [<transcription_file>]

## How to use

#### Transcribe a YouTube Video

The app can be used to directly transcribe a YouTube Video like this:

```python
python app.py https://www.youtube.com/watch?v=dQw4w9WgXcQ 2
```

Here, the parameters are as follows:

- YouTube_URL: The URL of the YouTube video to transcribe
- num_splits: The number of audio files to split the video into. Defaults to 5

#### Transcribe a Local Audio/Video File
The app can be used to transcribe a local Audio/Video file like this:
```python app.py /path/to/local/audio_or_video_file 2```

Here, the parameters are as follows:

- Audio/Video_File: The path of the local Audio/Video file to transcribe
- num_splits: The number of audio files to split the video into. Defaults to 5


#### Transcribe a list of YouTube videos stored in the csv file called youtube_videos.csv
The app can be used to transcribe a list of YouTube videos stored in the csv file called youtube_videos.csv like this:

```python batch_processor.py --splits 2```

Here, the parameters are as follows:

- splits: The number of audio files to split each video into. Defaults to 10

Also, *youtube_videos.csv* is the default csv file containing the list of YouTube videos to transcribe.


## How the app works
For each YouTube video or Audio/Video file, the app does the following:

- Downloads the YouTube video or processes the local Audio/Video file
- Splits the video into the specified number of audio files
- Transcribes each audio file, using a back-off strategy if the transcription fails due to a timeout
- Writes the transcription to a file in the "output" folder
- Deletes the split audio files and the original audio/video file from the "working" folder

Here:

- YouTube_URL or Audio/Video_File: The URL or Path of the YouTube video or local Audio/Video file to transcribe. If a YouTube URL is provided, it's first downloaded and then split/transcribed. If a local Audio/Video file is provided, it's split/transcribed.
- num_splits: The number of audio files to split the video into. Defaults to 5
- output_file: The name of the output file. Defaults to the code of the YouTube video (e.g., dQw4w9WgXcQ in the example above)
- transcription_file: The name of the transcription file. Defaults to the output_file with a .txt extension (e.g., dQw4w9WgXcQ.txt in the example above)

You can use the batch_processor.py app and the youtube_videos.csv file to process a batch of YouTube videos. The youtube_videos.csv file contains a list of YouTube videos to process, and the batch_processor.py app will process each video in the list.

The app uses the *"working"* folder to store the downloaded audio/video files and the split audio files during processing. Once the transcription is complete, the split audio files and the original audio/video file are deleted from the "working" folder. The transcribed text files are stored in the *"output"* folder.


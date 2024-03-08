import sys
from pytube import YouTube
import requests
from dotenv import load_dotenv
import os
from audio_engine import split_audio
from urllib.parse import urlparse, parse_qs, unquote
import time
import logging
import glob
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type


load_dotenv()  # Load environment variables from .env file
# Configure logging to write to app.log file
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_video_id(youtube_url):
    """
    Extracts the video ID from a YouTube URL.

    Args:
        youtube_url (str): The YouTube URL.

    Returns:
        str: The video ID.

    Raises:
        ValueError: If the video ID could not be extracted.
    """
    # Remove unnecessary backslashes
    cleaned_url = youtube_url.replace('\\', '')

    # Parse the YouTube URL
    parsed_url = urlparse(cleaned_url)
    
    # Extract the video ID from the query parameters
    video_id = parse_qs(parsed_url.query).get('v')
    
    if video_id:
        return video_id[0]
    else:
        logging.error("Invalid YouTube URL. Could not extract video ID.")
        raise ValueError("Invalid YouTube URL. Could not extract video ID.")

def download_youtube_video(youtube_url):
    """
    Downloads the YouTube video as an audio file.

    Args:
        youtube_url (str): The YouTube URL.

    Returns:
        str: The filename of the downloaded video.
    """
    video_id = extract_video_id(youtube_url)
    yt = YouTube(youtube_url)
    video = yt.streams.filter(only_audio=True).first()
    modified_filename = f"{video_id}_{video.default_filename}"
    video.download(filename=modified_filename)
    logging.info(f"Downloaded video to {modified_filename}")
    return modified_filename


@retry(stop=stop_after_attempt(10), wait=wait_fixed(15), retry=retry_if_exception_type(Exception))
def transcribe_audio(audio_file):
    """
    Transcribes an audio file using the Azure Speech Service.

    Args:
        audio_file (str): The audio file to transcribe.

    Returns:
        dict: The transcription result.

    Raises:
        Exception: If the rate limit is exceeded after several attempts.
    """
    headers = {'api-key': os.getenv('AZURE_KEY')}
    url = os.getenv('WHISPER_ENDPOINT')

    with open(audio_file, 'rb') as audio:
        files = {'file': audio}
        response = requests.post(url, headers=headers, files=files)
        logging.info(f"Transcription attempt on {audio_file}")    

        if response.status_code == 429:
            logging.error(f"Rate limit exceeded, retrying in 15 seconds for {audio_file}...")
            print(f"Rate limit exceeded, retrying in 15 seconds for {audio_file}...")
            raise Exception("Rate limit exceeded")
        else:
            logging.info(f"Succeeded for {audio_file}!")
            response.raise_for_status()
            return response.json()


def split_audio_with_prefix(audio_file, num_splits, output_prefix=None):
    """
    Splits an audio file into multiple parts with a specific prefix.

    Args:
        audio_file (str): The audio file to split.
        num_splits (int): The number of splits.
        output_prefix (str, optional): The prefix for the output files. Defaults to None.
    """
    if output_prefix is None:
        video_id = audio_file.split('_')[0]
        output_prefix = video_id
    safe_prefix = ''.join(c if c.isalnum() or c == '_' else '_' for c in output_prefix)
    split_audio(audio_file, num_splits, safe_prefix)

def delete_files(pattern):
    """
    Deletes files that match a specific pattern.

    Args:
        pattern (str): The pattern to match.
    """
    files = glob.glob(pattern)
    for file in files:
        os.remove(file)
    print(f"Deleted files: {pattern}")

def process_video(input:str, num_splits=5, output_file=None, transcription_file=None):
    """
    Processes a YouTube video or local file by downloading it (if necessary), splitting the audio, transcribing the audio, and saving the transcription.

    Args:
        input (str): The YouTube URL or local file path.
        num_splits (int, optional): The number of splits for the audio. Defaults to 5.
        output_file (str, optional): The output file for the transcription. Defaults to None.
        transcription_file (str, optional): The transcription file. Defaults to None.
    """
    start_time = datetime.now()

    if os.path.exists(input):
        logging.info(f"Processing local file {input}")
        video_file = input
    else:
        cleaned_url = unquote(input.replace('\\', ''))
        logging.info(f"Downloading video from {cleaned_url}")
        video_file = download_youtube_video(cleaned_url)

    if output_file is None:
        video_id = video_file.split('_')[0]
        output_file = f"{video_id}.txt"

    split_audio_with_prefix(video_file, num_splits)

    transcription_results = []
    for i in range(num_splits):
        video_id = video_file.split('_')[0]
        safe_prefix = ''.join(c if c.isalnum() or c == '_' else '_' for c in video_id)
        split_file_name = f"{safe_prefix}_{i+1}.m4a"
        transcription = transcribe_audio(split_file_name)
        logging.info(f"Transcribed: {split_file_name}")
        transcription_results.append(transcription['text'])

    with open(output_file, 'w') as file:
        file.writelines(transcription_results)

    if os.getenv('DELETE_AUDIO_FILES').lower() == 'true':
        logging.info("Deleting audio files...")
        delete_files('*.m4a')
        delete_files('*.mp4')
    else:
        logging.info("Skipping deletion of audio files")

    end_time = datetime.now()
    logging.info(f"Done! Runtime took {end_time - start_time}.")


if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 5:
        print("Usage: python app.py <YouTube URL> [<num_splits>] [<output_file>] [<transcription_file>]")
        sys.exit(1)

    process_video(sys.argv[1], 
                  int(sys.argv[2]) if len(sys.argv) > 2 else 5, 
                  sys.argv[3] if len(sys.argv) > 3 else None, 
                  sys.argv[4] if len(sys.argv) > 4 else None)

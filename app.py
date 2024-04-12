import sys
import os
from pytube import YouTube
import requests
from dotenv import load_dotenv
from audio_engine import split_audio
from urllib.parse import urlparse, parse_qs, unquote
import logging
import glob
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from rich.progress import Progress

WORKING_DIRECTORY = 'working'
OUTPUT_DIRECTORY = 'output'

load_dotenv()  # Load environment variables from .env file
# Configure logging to write to app.log file
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)
        logging.info(f"Created directory: {directory}")

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
    video.download(output_path=WORKING_DIRECTORY, filename=modified_filename)
    logging.info(f"Downloaded video to {os.path.join(WORKING_DIRECTORY, modified_filename)}")
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
            logging.warning(f"Rate limit exceeded, retrying in 15 seconds for {audio_file}...")
            raise Exception("Rate limit exceeded")
        else:
            logging.info(f"Transcription succeeded for {audio_file}")
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
        video_id = os.path.basename(audio_file).split('_')[0]
        output_prefix = video_id
    safe_prefix = ''.join(c if c.isalnum() or c == '_' else '_' for c in output_prefix)
    output_directory = os.path.dirname(audio_file)
    logging.info(f"Splitting audio file: {audio_file}")
    logging.info(f"Output prefix: {safe_prefix}")
    split_audio(audio_file, num_splits, safe_prefix, output_directory)
    logging.info(f"Split audio files saved in: {output_directory}")

def delete_files(pattern):
    """
    Deletes files that match a specific pattern in the working directory.

    Args:
        pattern (str): The pattern to match.
    """
    files = glob.glob(os.path.join(WORKING_DIRECTORY, pattern))
    for file in files:
        os.remove(file)
    logging.info(f"Deleted files: {pattern} in {WORKING_DIRECTORY}")

def process_video(input:str, num_splits=5, transcription_file=None, progress_callback=None):
    """
    Processes a YouTube video or local file by downloading it (if necessary), splitting the audio, transcribing the audio, and saving the transcription.

    Args:
        input (str): The YouTube URL or local file path.
        num_splits (int, optional): The number of splits for the audio. Defaults to 5.
        transcription_file (str, optional): The transcription file. Defaults to None.
        progress_callback (function, optional): A callback function to report progress. Defaults to None.
    """
    start_time = datetime.now()

    create_directory(WORKING_DIRECTORY)
    create_directory(OUTPUT_DIRECTORY)

    if os.path.exists(input):
        logging.info(f"Processing local file {input}")
        video_file = os.path.join(WORKING_DIRECTORY, os.path.basename(input))
        os.rename(input, video_file)
    else:
        cleaned_url = unquote(input.replace('\\', ''))
        logging.info(f"Downloading video from {cleaned_url}")
        video_file = download_youtube_video(cleaned_url)
        video_file = os.path.join(WORKING_DIRECTORY, video_file)
        if progress_callback:
            progress_callback("Downloaded video")

    logging.info(f"Video file: {video_file}")

    if transcription_file is None:
        video_id = os.path.basename(video_file).split('_')[0]
        transcription_file = f"{video_id}.txt"

    split_audio_with_prefix(video_file, num_splits)
    if progress_callback:
        progress_callback("Split audio")

    transcription_results = []
    for i in range(num_splits):
        video_id = os.path.basename(video_file).split('_')[0]
        safe_prefix = ''.join(c if c.isalnum() or c == '_' else '_' for c in video_id)
        split_file_name = os.path.join(WORKING_DIRECTORY, f"{safe_prefix}_{i+1}.m4a")
        logging.info(f"Transcribing split audio file: {split_file_name}")
        
        if not os.path.exists(split_file_name):
            logging.error(f"Split audio file not found: {split_file_name}")
            raise FileNotFoundError(f"Split audio file not found: {split_file_name}")
        
        transcription = transcribe_audio(split_file_name)
        logging.info(f"Transcribed: {split_file_name}")
        transcription_results.append(transcription['text'])
        
        # Delete the split audio file after transcription
        os.remove(split_file_name)
        logging.info(f"Deleted split audio file: {split_file_name}")
        
        if progress_callback:
            progress_callback(f"Transcribed part {i+1}")

    output_file_path = os.path.join(OUTPUT_DIRECTORY, transcription_file)
    with open(output_file_path, 'w') as file:
        file.write('\n'.join(transcription_results))
    logging.info(f"Transcription saved to: {output_file_path}")

    # Delete the video file after processing
    os.remove(video_file)
    logging.info(f"Deleted video file: {video_file}")

    end_time = datetime.now()
    logging.info(f"Done! Runtime took {end_time - start_time}.")


if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 4:
        print("Usage: python app.py <YouTube URL> [<num_splits>] [<transcription_file>]")
        sys.exit(1)

    youtube_url = sys.argv[1]
    num_splits = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    transcription_file = sys.argv[3] if len(sys.argv) > 3 else None

    def progress_callback(stage):
        print(f"  {stage}")

    try:
        process_video(input=youtube_url, num_splits=num_splits, transcription_file=transcription_file, progress_callback=progress_callback)
    except Exception as e:
        logging.error(f"Error processing {youtube_url}: {str(e)}")
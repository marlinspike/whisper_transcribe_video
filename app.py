import sys
from pytube import YouTube
import requests
from dotenv import load_dotenv
import os
from audio_engine import split_audio
from urllib.parse import urlparse, parse_qs
from urllib.parse import unquote
import time
import logging
import glob
from datetime import datetime

load_dotenv()  # Load environment variables from .env file
# Configure logging to write to app.log file
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def extract_video_id(youtube_url):
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
    Download the YouTube video as an audio file
    """
    # Extract the video ID from the URL
    video_id = extract_video_id(youtube_url)
    
    yt = YouTube(youtube_url)
    video = yt.streams.filter(only_audio=True).first()
    
    # Generate the modified filename by adding the video ID as a prefix
    modified_filename = f"{video_id}_{video.default_filename}"
    
    # Download the video with the modified filename
    video.download(filename=modified_filename)
    logging.info(f"Downloaded video to {modified_filename}")
    return modified_filename




def transcribe_audio(audio_file):
    headers = {
        'api-key': os.getenv('AZURE_KEY')
    }
    url = os.getenv('WHISPER_ENDPOINT')
    max_retries = 10
    retry_delay = 15  # Delay in seconds

    for attempt in range(max_retries):
        with open(audio_file, 'rb') as audio:
            files = {'file': audio}
            response = requests.post(url, headers=headers, files=files)
            logging.info(f"Transcription attempt {attempt+1}/{max_retries} on {audio_file}")    

            if response.status_code == 429:
                logging.error(f"Rate limit exceeded, retrying in {retry_delay} seconds for {audio_file}...")
                print(f"Rate limit exceeded, retrying in {retry_delay} seconds for {audio_file}...")
                time.sleep(retry_delay)
            else:
                response.raise_for_status()
                return response.json()
    raise Exception("Rate Limit Exceeded. Failed to transcribe after several attempts.")



def split_audio_with_prefix(audio_file, num_splits, output_prefix=None):
    """
    Split the audio file into multiple pieces
    """
    if output_prefix is None:
        # Extract the video ID from the audio_file name (assuming it's in the format "video_id_filename")
        video_id = audio_file.split('_')[0]
        output_prefix = video_id

    # Replace spaces and special characters in the prefix with underscores
    safe_prefix = ''.join(c if c.isalnum() or c == '_' else '_' for c in output_prefix)

    split_audio(audio_file, num_splits, safe_prefix)

def delete_files(pattern):
    files = glob.glob(pattern)
    for file in files:
        os.remove(file)
    print(f"Deleted files: {pattern}")


def main():
    start_time = datetime.now()
    if len(sys.argv) < 2 or len(sys.argv) > 5:
        print("Usage: python app.py <YouTube URL> [<num_splits>] [<output_file>] [<transcription_file>]")
        sys.exit(1)

    logging.info(f"Running with arguments: {sys.argv}")
    youtube_url = sys.argv[1]

    # Preprocess the URL to remove backslashes and handle percent-encoding
    cleaned_url = unquote(youtube_url.replace('\\', ''))

    num_splits = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    output_file = sys.argv[3] if len(sys.argv) > 3 else None
    transcription_file = sys.argv[4] if len(sys.argv) > 4 else None

    print("Downloading video...")
    logging.info(f"Downloading video from {cleaned_url}")
    video_file = download_youtube_video(cleaned_url)


    # Check if output_file is None and set it to the default value
    if output_file is None:
        # Extract the video ID from the video_file name (assuming it's in the format "video_id_filename")
        video_id = video_file.split('_')[0]
        output_file = f"{video_id}.txt"

    print(f"Splitting the audio into {num_splits} pieces...")
    split_audio_with_prefix(video_file, num_splits)

    transcription_results = []
    for i in range(num_splits):
        # Extract the video ID from the video_file name (assuming it's in the format "video_id_filename")
        video_id = video_file.split('_')[0]
        safe_prefix = ''.join(c if c.isalnum() or c == '_' else '_' for c in video_id)
        split_file_name = f"{safe_prefix}_{i+1}.m4a"  # Corrected prefix
        print(f"Transcribing {split_file_name}...")
        transcription = transcribe_audio(split_file_name)
        transcription_results.append(transcription['text'])

    with open(output_file, 'w') as file:
        file.writelines(transcription_results)
    print(f"Transcription saved to {output_file}")

    # Check if DELETE_AUDIO_FILES is set to True in the .env file
    if os.getenv('DELETE_AUDIO_FILES').lower() == 'true':
        print("Deleting audio files...")
        logging.info("Deleting audio files...")
        delete_files('*.m4a')
        delete_files('*.mp4')
    else:
        logging.info("Skipping deletion of audio files")

    end_time = datetime.now()

    logging.info(f"Done! Runtime took {end_time - start_time} seconds.")
if __name__ == "__main__":
    main()

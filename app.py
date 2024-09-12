import sys
from typing import List, Dict, Tuple, Any
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
import yt_dlp
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

load_dotenv()  # Load environment variables from .env file
# Configure logging to write to app.log file
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def display_rich_output(processed_files: List[str], file_times: Dict[str, float], total_time: float, output_files: List[str]) -> None:
    console = Console()
    table = Table(title="Processed Files", box=box.ROUNDED)
    table.add_column("File", style="cyan")
    table.add_column("Processing Time", style="magenta")
    for file in processed_files:
        table.add_row(file, f"{file_times[file]:.2f} seconds")
    summary = f"[bold green]Total Time:[/bold green] {total_time:.2f} seconds\n"
    summary += "[bold blue]Output File(s):[/bold blue]\n" + "\n".join(f"- {file}" for file in output_files)
    console.print(Panel(table, expand=False))
    console.print(Panel(summary, title="Summary", expand=False))


def process_video(input: str, num_splits: int = 5, output_file: str = None, transcription_file: str = None, output_directory: str = None) -> None:
    start_time = datetime.now()
    processed_files: List[str] = []
    file_times: Dict[str, float] = {}
    output_files: List[str] = []

    try:
        if os.path.exists(input):
            logging.info(f"Processing local file {input}")
            video_file = input
        else:
            cleaned_url = unquote(input.replace('\\', ''))
            logging.info(f"Downloading video from {cleaned_url}")
            video_file = download_youtube_video(cleaned_url)

        processed_files.append(video_file)
        file_start_time = datetime.now()

        if output_file is None:
            video_id = video_file.split('_')[0]
            output_file = f"{video_id}.txt"

        # Create the output directory if it doesn't exist
        output_directory = os.path.join(os.getcwd(), "output")
        os.makedirs(output_directory, exist_ok=True)
        logging.info(f"Output directory ensured: {output_directory}")

        # Set the full path for the output file
        output_file_path = os.path.join(output_directory, output_file)

        # Use the current working directory for temporary files
        temp_directory = os.getcwd()

        split_audio_with_prefix(video_file, num_splits, temp_directory)

        transcription_results: List[str] = []
        for i in range(num_splits):
            video_id = video_file.split('_')[0]
            safe_prefix = ''.join(c if c.isalnum() or c == '_' else '_' for c in video_id)
            split_file_name = f"{safe_prefix}_{i+1}.m4a"
            split_file_path = os.path.join(temp_directory, split_file_name)
            transcription = transcribe_audio(split_file_path)
            logging.info(f"Transcribed: {split_file_name}")
            transcription_results.append(transcription['text'])

        # Write the transcription to the output file, overwriting if it exists
        with open(output_file_path, 'w') as file:
            file.writelines(transcription_results)
        logging.info(f"Transcription saved to: {output_file_path}")

        output_files.append(output_file_path)
        file_end_time = datetime.now()
        file_times[video_file] = (file_end_time - file_start_time).total_seconds()

        if os.getenv('DELETE_AUDIO_FILES', 'false').lower() == 'true':
            logging.info("Deleting audio files...")
            delete_files(os.path.join(temp_directory, '*.m4a'))
            delete_files('*.mp4')
        else:
            logging.info("Skipping deletion of audio files")

    except Exception as e:
        logging.error(f"Error in process_video: {str(e)}")
        file_times[video_file] = 0  # Set a default time if processing failed
    finally:
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        logging.info(f"Done! Runtime took {total_time:.2f} seconds.")
        
        # Display rich output
        display_rich_output(processed_files, file_times, total_time, output_files)


def extract_video_id(youtube_url: str) -> str:
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

def download_youtube_video(youtube_url: str) -> str:
    try:
        video_id = extract_video_id(youtube_url)
        ydl_opts: Dict[str, Any] = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
            }],
            'outtmpl': f'{video_id}_%(title)s.%(ext)s'
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            filename = ydl.prepare_filename(info)
            filename = filename.rsplit('.', 1)[0] + '.m4a'  # Change extension to .m4a
        
        logging.info(f"Downloaded video to {filename}")
        return filename
    except Exception as e:
        logging.error(f"Error in download_youtube_video: {str(e)}")
        raise  # Re-raise the exception after logging it


@retry(stop=stop_after_attempt(10), wait=wait_fixed(15), retry=retry_if_exception_type(Exception))
def transcribe_audio(audio_file: str) -> Dict[str, Any]:
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


def split_audio_with_prefix(audio_file: str, num_splits: int, output_directory: str, output_prefix: str = None) -> None:
    if output_prefix is None:
        video_id = audio_file.split('_')[0]
        output_prefix = video_id
    safe_prefix = ''.join(c if c.isalnum() or c == '_' else '_' for c in output_prefix)
    split_audio(audio_file, num_splits, safe_prefix, output_directory)

def delete_files(pattern: str) -> None:
    files = glob.glob(pattern)
    for file in files:
        os.remove(file)
    print(f"Deleted files: {pattern}")


if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 5:
        print("Usage: python app.py <YouTube URL> [<num_splits>] [<output_file>] [<transcription_file>]")
        sys.exit(1)

    process_video(sys.argv[1], 
                  int(sys.argv[2]) if len(sys.argv) > 2 else 5, 
                  sys.argv[3] if len(sys.argv) > 3 else None, 
                  sys.argv[4] if len(sys.argv) > 4 else None)
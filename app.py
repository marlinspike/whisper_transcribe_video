import os
import sys
import logging
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs, unquote
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
import requests
import glob
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
import yt_dlp
from openai import OpenAI
from pydub import AudioSegment

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
USE_OPENAI_WHISPER: bool = os.getenv('USE_OPENAI_WHISPER', 'false').lower() == 'true'
AZURE_KEY: str = os.getenv('AZURE_KEY', '')
WHISPER_ENDPOINT: str = os.getenv('WHISPER_ENDPOINT', '')
OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY', '')

# Initialize OpenAI client
client = OpenAI()

# Helper Functions
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

@retry(stop=stop_after_attempt(10), wait=wait_fixed(15), retry=retry_if_exception_type(Exception))
def transcribe_audio(audio_file: str) -> Dict[str, Any]:
    """Transcribes audio using the selected Whisper endpoint."""
    if USE_OPENAI_WHISPER:
        try:
            logging.info(f"Using OpenAI Whisper to transcribe {audio_file}")
            with open(audio_file, "rb") as audio:
                result = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio
                )
            logging.info(f"Transcription result for {audio_file}: {result}")
            return result
        except Exception as e:
            logging.error(f"OpenAI Whisper error: {str(e)}")
            raise
    else:
        headers = {'api-key': AZURE_KEY}
        url = WHISPER_ENDPOINT

        with open(audio_file, 'rb') as audio:
            files = {'file': audio}
            response = requests.post(url, headers=headers, files=files)

            if response.status_code == 429:
                logging.warning(f"Rate limit exceeded for {audio_file}, retrying...")
                raise Exception("Rate limit exceeded")

            response.raise_for_status()
            result = response.json()
            logging.info(f"Transcription result for {audio_file}: {result}")
            return result

def delete_files(pattern: str) -> None:
    """Deletes files matching the provided pattern."""
    files = glob.glob(pattern)
    for file in files:
        os.remove(file)
    logging.info(f"Deleted files matching pattern: {pattern}")

def delete_individual_files(files: List[str]) -> None:
    """Deletes a list of specific files."""
    for file in files:
        try:
            os.remove(file)
            logging.info(f"Deleted file: {file}")
        except FileNotFoundError:
            logging.warning(f"File not found, skipping: {file}")

def download_youtube_video(youtube_url: str) -> str:
    """Downloads a YouTube video as an audio file."""
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
            filename = filename.rsplit('.', 1)[0] + '.m4a'  # Ensure .m4a extension

        logging.info(f"Downloaded video to {filename}")
        return filename
    except Exception as e:
        logging.error(f"Error in download_youtube_video: {str(e)}")
        raise

def extract_video_id(youtube_url: str) -> str:
    """Extracts the video ID from a YouTube URL."""
    cleaned_url = unquote(youtube_url.replace('\\', ''))  # Unescape escaped characters
    parsed_url = urlparse(cleaned_url)
    if parsed_url.netloc == "youtu.be":
        video_id = parsed_url.path.lstrip('/')  # Handle youtu.be short URLs
    else:
        video_id = parse_qs(parsed_url.query).get('v', [None])[0]  # Handle full YouTube URLs
    
    if video_id:
        return video_id
    else:
        logging.error("Invalid YouTube URL. Could not extract video ID.")
        raise ValueError("Invalid YouTube URL. Could not extract video ID.")

def split_audio(audio_file: str, num_splits: int, output_directory: str) -> List[str]:
    """Splits an audio file into smaller segments."""
    audio = AudioSegment.from_file(audio_file)
    segment_length = len(audio) // num_splits
    output_files = []

    for i in range(num_splits):
        start = i * segment_length
        end = (i + 1) * segment_length if i < num_splits - 1 else len(audio)
        segment = audio[start:end]

        segment_filename = os.path.join(output_directory, f"{os.path.splitext(os.path.basename(audio_file))[0]}_part{i + 1}.m4a")
        segment.export(segment_filename, format="ipod")  # Use 'ipod' for reliable m4a export
        output_files.append(segment_filename)

    return output_files

def process_video(input: str, num_splits: int = 5, output_file: str = None) -> None:
    """Processes video/audio input and transcribes it."""
    start_time = datetime.now()
    processed_files: List[str] = []
    file_times: Dict[str, float] = {}
    output_files: List[str] = []
    video_file: str = ""  # Initialize video_file to prevent unbound error

    try:
        if os.path.exists(input):
            logging.info(f"Processing local file: {input}")
            video_file = input
        else:
            logging.info(f"Processing YouTube URL: {input}")
            video_file = download_youtube_video(input)

        processed_files.append(video_file)
        file_start_time = datetime.now()

        # Ensure output directory
        output_directory = os.path.join(os.getcwd(), "output")
        os.makedirs(output_directory, exist_ok=True)

        # Split audio into smaller segments
        split_files = split_audio(video_file, num_splits, output_directory)

        transcription_results: List[str] = []
        for part_file in split_files:
            transcription = transcribe_audio(part_file)
            if hasattr(transcription, 'text'):
                transcription_results.append(transcription.text)
            else:
                logging.error(f"No text in transcription result for {part_file}: {transcription}")
                transcription_results.append("[No transcription generated]")

        # Save transcription
        if output_file is None:
            video_id = os.path.basename(video_file).split('_')[0]
            output_file = f"{video_id}.txt"

        output_file_path = os.path.join(output_directory, output_file)
        with open(output_file_path, 'w') as file:
            file.writelines(transcription_results)

        logging.info(f"Transcription saved to: {output_file_path}")
        output_files.append(output_file_path)
        file_end_time = datetime.now()
        file_times[video_file] = (file_end_time - file_start_time).total_seconds()

        # Delete intermediate files
        delete_individual_files(split_files)
        if os.getenv('DELETE_AUDIO_FILES', 'false').lower() == 'true':
            delete_individual_files([video_file])

    except Exception as e:
        logging.error(f"Error processing video: {str(e)}")
        if video_file:
            file_times[video_file] = 0
    finally:
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        display_rich_output(processed_files, file_times, total_time, output_files)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python app.py <input> [num_splits] [output_file]")
        sys.exit(1)

    input_file_or_url = sys.argv[1]
    num_splits = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    output_file = sys.argv[3] if len(sys.argv) > 3 else None

    logging.info(f"Starting process_video with input: {input_file_or_url}, num_splits: {num_splits}, output_file: {output_file}")
    process_video(input_file_or_url, num_splits, output_file)

from pydub import AudioSegment
import logging
import os

# Configure logging to write to app.log file
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def split_audio(audio_file, num_splits, output_prefix, output_directory):
    """
    Splits an audio file into multiple parts.

    Args:
        audio_file (str): The audio file to split.
        num_splits (int): The number of splits.
        output_prefix (str): The prefix for the output files.
        output_directory (str): The directory to save the split audio files.
    """
    audio = AudioSegment.from_file(audio_file, format="mp4")
    duration = len(audio)
    split_duration = duration // num_splits

    for i in range(num_splits):
        start_time = i * split_duration
        end_time = (i + 1) * split_duration if i < num_splits - 1 else duration
        split_audio = audio[start_time:end_time]
        output_file = f"{output_prefix}_{i+1}.m4a"
        split_audio.export(os.path.join(output_directory, output_file), format="mp4")
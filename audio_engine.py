from pydub import AudioSegment
import logging

# Configure logging to write to app.log file
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def split_audio(file_name, num_splits, output_prefix):
    # Load the audio file
    audio = AudioSegment.from_file(file_name)

    # Calculate the length of each split
    split_length = len(audio) // num_splits

    for i in range(num_splits):
        # Calculate start and end of the split
        start = i * split_length
        end = start + split_length if i < num_splits - 1 else len(audio)

        # Extract the split
        split_audio = audio[start:end]

        # Generate split file name
        split_file_name = f"{output_prefix}_{i+1}.m4a"

        # Export the split to a file
        split_audio.export(split_file_name, format="mp3")
        print(f"Exported: {split_file_name}")
        logging.info(f"Exported: {split_file_name}")
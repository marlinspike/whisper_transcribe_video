import csv
from app import process_video
import logging
import argparse
from rich.progress import Progress, TaskID

# Configure logging to write to app.log file
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set up argument parsing
parser = argparse.ArgumentParser(description='Process videos and split audio into chunks.')
parser.add_argument('--splits', type=int, default=10, help='Number of splits to divide the audio into')

# Parse arguments
args = parser.parse_args()

def process_csv(csv_file: str) -> None:
    """
    Processes a CSV file where each row contains a YouTube URL.

    Args:
        csv_file (str): The CSV file to process.
    """
    # Log the start of the batch processing
    logging.info(f"Processing Batch File {csv_file}...")

    # Open the CSV file
    with open(csv_file, newline='') as file:
        # Create a CSV reader
        reader = csv.reader(file)
        
        # Get the total number of rows in the CSV file
        total_rows = sum(1 for _ in reader)
        file.seek(0)  # Reset the file pointer to the beginning
        
        # Create a progress bar for total progress
        with Progress() as progress:
            total_task = progress.add_task("Total Progress", total=total_rows)
            
            # Process each row in the CSV file
            for row in reader:
                # Get the YouTube URL from the row
                youtube_url = row[0]
                print(youtube_url)
                
                # Log and print the YouTube URL being processed
                logging.info(f"Processing {youtube_url}...")
                print(f"Processing {youtube_url}...")
                
                # Create a progress bar for per-file progress
                per_file_task = progress.add_task(f"Processing {youtube_url}", total=args.splits + 2)
                
                try:
                    # Process the YouTube video
                    def progress_callback(stage):
                        progress.update(per_file_task, advance=1, description=f"Processing {youtube_url} - {stage}")
                        print(f"  {stage}")
                    
                    process_video(num_splits=args.splits, input=youtube_url, progress_callback=progress_callback)
                except Exception as e:
                    logging.error(f"Error processing {youtube_url}: {str(e)}")
                
                progress.update(total_task, advance=1)

# If this script is run directly (not imported), process the CSV file
if __name__ == "__main__":
    # The CSV file to process
    csv_file = 'youtube_videos.csv'
    
    # Process the CSV file
    process_csv(csv_file)
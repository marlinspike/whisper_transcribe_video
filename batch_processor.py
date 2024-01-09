import csv
from app import process_video
import logging

# Configure logging to write to app.log file
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_csv(csv_file):
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
        
        # Process each row in the CSV file
        for row in reader:
            # Get the YouTube URL from the row
            youtube_url = row[0]
            
            # Log and print the YouTube URL being processed
            logging.info(f"Processing {youtube_url}...")
            print(f"Processing {youtube_url}...")
            
            # Process the YouTube video
            process_video(youtube_url = youtube_url)

# If this script is run directly (not imported), process the CSV file
if __name__ == "__main__":
    # The CSV file to process
    csv_file = 'youtube_videos.csv'
    
    # Process the CSV file
    process_csv(csv_file)
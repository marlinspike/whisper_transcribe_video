import csv
from app import process_video
import logging

# Configure logging to write to app.log file
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_csv(csv_file):
    logging.info(f"Processing Batch File {csv_file}...")
    with open(csv_file, newline='') as file:
        reader = csv.reader(file)
        for row in reader:
            youtube_url = row[0]
            logging.info(f"Processing {youtube_url}...")
            print(f"Processing {youtube_url}...")
            process_video(youtube_url = youtube_url)

if __name__ == "__main__":
    csv_file = 'youtube_videos.csv'
    process_csv(csv_file)
import requests
import os
import random
import string
import sys

def download_file(url, file_name=None):
    # Send a GET request to the URL
    response = requests.get(url)

    # Ensure the request was successful (status code 200)
    if response.status_code == 200:
        # Generate a random file name if none was provided
        if file_name is None:
            file_ext = url.split('.')[-1]  # Get the file extension from the URL
            random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=10))  # Generate a random string
            file_name = f'{random_str}.{file_ext}'

        # Write the binary content to the output file
        with open(file_name, 'wb') as file:
            file.write(response.content)
        print(f'File downloaded successfully at {file_name}')
    else:
        print(f'Failed to download file. Status code: {response.status_code}')

def main():
    if len(sys.argv) < 2:
        print("Usage: python download_file.py <URL> [output_file_name]")
        sys.exit(1)

    url = sys.argv[1]
    file_name = sys.argv[2] if len(sys.argv) > 2 else None

    download_file(url, file_name)

if __name__ == "__main__":
    main()

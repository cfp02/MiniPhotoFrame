
import time
from drive_auth import authenticate_google_drive
from drive_manager import create_drive_service, list_photos, download_photo
from display_manager import show_photo

def run_digital_picture_frame(folder_id=None):
    creds = authenticate_google_drive()
    service = create_drive_service(creds)
    while True:
        photos = list_photos(service, folder_id)
        for photo in photos:
            file_name = photo['name']
            download_photo(service, photo['id'], file_name)
            show_photo(file_name)
            time.sleep(10)  # Display each photo for 10 seconds

if __name__ == "__main__":
    run_digital_picture_frame(folder_id="1uqSiuVgeeYTMnmHnlfIi1j4N_D_XzppG")

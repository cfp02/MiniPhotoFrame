
import time
import os
from drive_auth import authenticate_google_drive
from drive_manager import create_drive_service, list_photos, download_photo
from display_manager import show_photo

base_path = os.path.dirname(os.path.realpath(__file__))

def sync_drive_images(service, folder_id, local_folder):
    # Ensure the local folder exists
    if not os.path.exists(local_folder):
        os.makedirs(local_folder)

    # Step 1: Get list of photos in Google Drive
    drive_photos = list_photos(service, folder_id)
    drive_photo_ids = {photo['id']: photo['name'] for photo in drive_photos}
    drive_photo_names = set(drive_photo_ids.values())

    # Step 2: Get list of photos in the local folder
    local_photo_names = set(os.listdir(local_folder))
    for local_photo in local_photo_names:
        if local_photo == ".gitkeep":
            continue

    # Step 3: Delete extra photos in the local folder
    for local_photo in local_photo_names - drive_photo_names:
        os.remove(os.path.join(local_folder, local_photo))
        print(f"Deleted extra local photo: {local_photo}")

    # Step 4: Download missing photos from Google Drive
    for photo_id, photo_name in drive_photo_ids.items():
        if photo_name not in local_photo_names:
            download_photo(service, photo_id, os.path.join(local_folder, photo_name))
            print(f"Downloaded photo: {photo_name}")

def run_digital_picture_frame(folder_id, local_image_folder, display_interval):
    # Step 1: Authenticate and create the Drive service
    creds = authenticate_google_drive()
    service = create_drive_service(creds)

    # Step 2: Sync images between Google Drive and the local folder
    sync_drive_images(service, folder_id, local_image_folder)

    # Step 3: Start the slideshow
    while True:
        print("Restarting")
        for photo_name in os.listdir(local_image_folder):
            photo_path = os.path.join(local_image_folder, photo_name)
            show_photo(photo_path)
            time.sleep(display_interval)

if __name__ == "__main__":
    # Define your input parameters
    folder_id = "1uqSiuVgeeYTMnmHnlfIi1j4N_D_XzppG"            # Google Drive folder ID
    local_image_folder = "images"                # Local folder to store images
    local_folder_path = os.path.join(base_path, local_image_folder)
    display_interval = 10                        # Interval in seconds between photos

    run_digital_picture_frame(folder_id, local_folder_path, display_interval)



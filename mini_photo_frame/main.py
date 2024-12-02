import time
import os
import random
from drive_auth import authenticate_google_drive
from drive_manager import create_drive_service, list_photos, download_photo
from display_manager import show_photo
from datetime import datetime, timedelta

base_path = os.path.dirname(os.path.realpath(__file__))

def sync_drive_images(service, folder_id, local_folder):
    """Syncs images and returns a list of any new photos downloaded"""
    # Ensure the local folder exists
    if not os.path.exists(local_folder):
        os.makedirs(local_folder)

    # Step 1: Get list of photos in Google Drive (sorted by creation time)
    drive_photos = list_photos(service, folder_id)
    drive_photo_ids = {photo['id']: photo for photo in drive_photos}
    drive_photo_names = set(photo['name'] for photo in drive_photos)

    # Step 2: Get list of photos in the local folder
    local_photo_names = set(os.listdir(local_folder))
    if ".gitkeep" in local_photo_names:
        local_photo_names.remove(".gitkeep")

    # Step 3: Delete extra photos in the local folder
    for local_photo in local_photo_names - drive_photo_names:
        os.remove(os.path.join(local_folder, local_photo))
        print(f"Deleted extra local photo: {local_photo}")

    # Step 4: Download missing photos from Google Drive
    new_photos = []
    for photo_id, photo_info in drive_photo_ids.items():
        photo_name = photo_info['name']
        if photo_name not in local_photo_names:
            download_photo(service, photo_id, os.path.join(local_folder, photo_name))
            print(f"Downloaded new photo: {photo_name}")
            new_photos.append(photo_name)

    return new_photos, [photo['name'] for photo in drive_photos]

def run_digital_picture_frame(folder_id, local_image_folder, display_interval):
    # Step 1: Authenticate and create the Drive service
    creds = authenticate_google_drive()
    service = create_drive_service(creds)

    # Initial sync
    new_photos, all_photos = sync_drive_images(service, folder_id, local_image_folder)
    last_sync_time = time.time()
    sync_interval = 300  # Check for new photos every 5 minutes

    while True:
        current_time = time.time()
        
        # Check for new photos periodically
        if current_time - last_sync_time >= sync_interval:
            print("Checking for new photos...")
            new_photos, all_photos = sync_drive_images(service, folder_id, local_image_folder)
            last_sync_time = current_time

        # Show new photos first, then shuffle and show all photos
        photos_to_display = new_photos.copy()  # Show new photos in chronological order
        remaining_photos = [p for p in all_photos if p not in new_photos]
        random.shuffle(remaining_photos)  # Shuffle the remaining photos
        photos_to_display.extend(remaining_photos)  # Add shuffled photos after new ones
        new_photos = []  # Clear new photos list after displaying them

        for photo_name in photos_to_display:
            photo_path = os.path.join(local_image_folder, photo_name)
            if not os.path.exists(photo_path):
                continue
                
            print(f"Showing photo: {photo_name}")
            key_pressed = show_photo(photo_path, display_interval)
            
            # Check for new photos if it's time
            current_time = time.time()
            if current_time - last_sync_time >= sync_interval:
                print("Checking for new photos...")
                new_photos, all_photos = sync_drive_images(service, folder_id, local_image_folder)
                last_sync_time = current_time
                if new_photos:  # If new photos were found, break the current loop to show them
                    break
            
            if key_pressed == 27:  # ESC key
                return

if __name__ == "__main__":
    # Define your input parameters
    folder_id = "1uqSiuVgeeYTMnmHnlfIi1j4N_D_XzppG"  # Google Drive folder ID
    local_image_folder = "images"                      # Local folder to store images
    local_folder_path = os.path.join(base_path, local_image_folder)
    display_interval = 60                         # 1 minute between photos

    run_digital_picture_frame(folder_id, local_folder_path, display_interval)



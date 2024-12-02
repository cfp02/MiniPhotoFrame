import time
import os
import random
import sys
from drive_auth import (
    authenticate_google_drive, 
    is_frozen, 
    get_base_path
)
from drive_manager import (
    create_drive_service, list_photos, download_photo,
    get_or_create_settings_folder, get_settings_from_folders,
    ensure_default_settings_folders
)
from display_manager import show_photo
from datetime import datetime, timedelta

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

def load_config():
    config = {
        'FOLDER_ID': None,
        'DISPLAY_INTERVAL': 45 * 60,  # 45 minutes default
        'SYNC_INTERVAL': 5 * 60,      # 5 minutes default
        'SHUFFLE': True,              # Shuffle by default after showing new photos
    }
    
    # Try to find config file in different locations
    possible_paths = [
        # Deployed mode: config.txt next to executable
        os.path.join(get_base_path(), 'config.txt'),
        # Development mode: config.txt in project root
        os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'config.txt'),
        # Fallback: config.txt in current directory
        'config.txt'
    ]
    
    config_path = None
    for path in possible_paths:
        if os.path.exists(path):
            config_path = path
            break
    
    if config_path:
        print(f"Using config file: {config_path}")
        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
        
        # Convert values to appropriate types
        config['DISPLAY_INTERVAL'] = int(config['DISPLAY_INTERVAL'])
        config['SYNC_INTERVAL'] = int(config['SYNC_INTERVAL'])
        if 'SHUFFLE' in config:
            config['SHUFFLE'] = config['SHUFFLE'].lower() == 'true'
    else:
        print("\nNo config.txt found. Using default settings.")
        if not is_frozen():
            print("Development mode: Create a config.txt file in the project root.")
    
    return config

def get_images_path():
    """Get the images directory path based on environment"""
    if is_frozen():
        # In deployed mode, images folder is next to the executable
        return os.path.join(get_base_path(), 'images')
    else:
        # In development mode, images folder is in the project directory
        return os.path.join(get_base_path(), 'mini_photo_frame', 'images')

def run_digital_picture_frame(folder_id, local_image_folder, service, settings):
    """Run the picture frame with the given settings"""
    # Initial sync
    new_photos, all_photos = sync_drive_images(service, folder_id, local_image_folder)
    last_sync_time = time.time()
    last_settings_check = time.time()
    settings_check_interval = 60  # Check settings every minute

    while True:
        current_time = time.time()
        
        # Check for settings updates periodically
        if current_time - last_settings_check >= settings_check_interval:
            settings_folder_id = get_or_create_settings_folder(service, folder_id)
            new_settings = get_settings_from_folders(service, settings_folder_id, settings)
            if new_settings != settings:
                print("Settings updated from Google Drive folders")
                settings.update(new_settings)
            last_settings_check = current_time
        
        # Check for new photos
        if current_time - last_sync_time >= settings['sync_interval']:
            print("Checking for new photos...")
            new_photos, all_photos = sync_drive_images(service, folder_id, local_image_folder)
            last_sync_time = current_time

        # Show new photos first, then shuffle remaining if enabled
        photos_to_display = new_photos.copy()
        remaining_photos = [p for p in all_photos if p not in new_photos]
        
        if settings['shuffle']:
            random.shuffle(remaining_photos)
        photos_to_display.extend(remaining_photos)
        new_photos = []

        for photo_name in photos_to_display:
            photo_path = os.path.join(local_image_folder, photo_name)
            if not os.path.exists(photo_path):
                continue
                
            print(f"Showing photo: {photo_name}")
            key_pressed = show_photo(photo_path, settings['display_interval'])
            
            # Check for updates during long display intervals
            current_time = time.time()
            if current_time - last_sync_time >= settings['sync_interval']:
                print("Checking for new photos...")
                new_photos, all_photos = sync_drive_images(service, folder_id, local_image_folder)
                last_sync_time = current_time
                if new_photos:
                    break
            
            if key_pressed == 27:  # ESC key
                return

def main():
    # Load configuration
    config = load_config()
    
    if not config['FOLDER_ID'] or config['FOLDER_ID'] == 'your_google_drive_folder_id_here':
        print("\nPlease set your Google Drive folder ID in config.txt")
        if not is_frozen():
            print("Development mode: Edit config.txt in the project root.")
        return

    # Get the correct images path
    local_image_folder = get_images_path()
    
    # Initialize service and settings
    creds = authenticate_google_drive()
    if not creds:
        return
        
    service = create_drive_service(creds)
    
    # Convert config to settings format
    settings = {
        'display_interval': config['DISPLAY_INTERVAL'],
        'sync_interval': config['SYNC_INTERVAL'],
        'shuffle': config.get('SHUFFLE', True),
        'filter': None
    }
    
    # Set up settings folders in Google Drive
    settings_folder_id = get_or_create_settings_folder(service, config['FOLDER_ID'])
    ensure_default_settings_folders(service, settings_folder_id, settings)
    
    # Get any existing settings from folders
    settings = get_settings_from_folders(service, settings_folder_id, settings)
    
    print("\nStarting photo frame...")
    print(f"Display interval: {settings['display_interval'] // 60} minutes")
    print(f"Sync interval: {settings['sync_interval'] // 60} minutes")
    print(f"Shuffle mode: {settings['shuffle']}")
    
    run_digital_picture_frame(config['FOLDER_ID'], local_image_folder, service, settings)

if __name__ == "__main__":
    main()



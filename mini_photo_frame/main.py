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
import logging

def load_config():
    """Load configuration from config.txt file"""
    config = {
        'FOLDER_ID': None,
        'DISPLAY_INTERVAL': 45 * 60,  # 45 minutes default
        'SYNC_INTERVAL': 5 * 60,      # 5 minutes default
        'SHUFFLE': True,              # Shuffle by default after showing new photos
        'LOG_LEVEL': 'INFO',          # Default logging level
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
        
        # Set logging level
        if 'LOG_LEVEL' in config:
            log_level = config['LOG_LEVEL'].upper()
            if log_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
                logging.getLogger().setLevel(getattr(logging, log_level))
                print(f"Setting log level to: {log_level}")
    else:
        print("\nNo config.txt found. Using default settings.")
        if not is_frozen():
            print("Development mode: Create a config.txt file in the project root.")
    
    return config

def sync_drive_images(service, folder_id, local_folder, settings=None):
    """Syncs images and returns a list of any new photos downloaded"""
    # Ensure the local folder exists
    if not os.path.exists(local_folder):
        os.makedirs(local_folder)

    # Step 1: Get list of photos in Google Drive (sorted by creation time)
    search_query = settings.get('search', '').lower() if settings else None
    shuffle_enabled = settings.get('shuffle', False) if settings else False
    drive_photos = list_photos(service, folder_id, search_query, shuffle_enabled)
    
    # Create a map of photo IDs to their full info
    drive_photo_ids = {photo['id']: photo for photo in drive_photos}
    
    # Get set of all photo paths (normalized)
    drive_photo_paths = {photo['path'].replace('\\', '/') for photo in drive_photos}
    local_photos = {}  # Map of relative paths to full local paths
    
    print("Scanning local files...")
    # Walk through local directory to build current state
    for root, _, files in os.walk(local_folder):
        for file in files:
            if file == ".gitkeep":
                continue
            # Get path relative to local_folder and normalize it
            rel_path = os.path.relpath(os.path.join(root, file), local_folder).replace('\\', '/')
            local_photos[rel_path] = os.path.join(root, file)
    
    # Track new photos for display priority
    new_photos = []
    
    # Process each photo from Drive
    for photo in drive_photos:
        # Use the full path from Drive (normalized)
        rel_path = photo['path'].replace('\\', '/')
        
        # Check if we need to download this photo
        if rel_path not in local_photos:
            # Ensure the directory exists
            photo_dir = os.path.dirname(os.path.join(local_folder, rel_path))
            if photo_dir and not os.path.exists(photo_dir):
                os.makedirs(photo_dir)
                
            # Download the photo
            local_path = os.path.join(local_folder, rel_path)
            download_photo(service, photo['id'], local_path)
            print(f"Downloaded new photo: {rel_path}")
            new_photos.append(rel_path)
    
    # Remove local photos that no longer exist in Drive
    photos_to_delete = set(local_photos.keys()) - drive_photo_paths
    if photos_to_delete:
        print(f"\nRemoving {len(photos_to_delete)} photos that no longer exist in Drive:")
        for rel_path in photos_to_delete:
            print(f"  Deleting: {rel_path}")
            try:
                os.remove(local_photos[rel_path])
                # Remove empty directories
                dir_path = os.path.dirname(local_photos[rel_path])
                while dir_path != local_folder:
                    try:
                        os.rmdir(dir_path)
                        dir_path = os.path.dirname(dir_path)
                    except OSError:  # Directory not empty
                        break
            except Exception as e:
                print(f"  Error deleting {rel_path}: {str(e)}")
    
    # Return paths for all photos, with new ones first
    all_paths = [p['path'] for p in drive_photos]
    if new_photos:
        # Remove new photos from all_paths to avoid duplicates
        all_paths = [p for p in all_paths if p not in new_photos]
        # Add new photos at the start
        all_paths = new_photos + all_paths
    
    return new_photos, all_paths


def validate_images_path(path):
    """Validate and create images directory if needed"""
    try:
        # Expand user path and resolve any symlinks
        path = os.path.realpath(os.path.expanduser(path))
        
        # Check if path exists
        if os.path.exists(path):
            if not os.path.isdir(path):
                return False, f"Path exists but is not a directory: {path}"
            # Check if we have write permission
            if not os.access(path, os.W_OK):
                return False, f"No write permission for directory: {path}"
        else:
            # Try to create the directory
            try:
                os.makedirs(path, exist_ok=True)
            except Exception as e:
                return False, f"Could not create directory {path}: {str(e)}"
        
        # Try to write a test file
        test_file = os.path.join(path, '.write_test')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
        except Exception as e:
            return False, f"Directory is not writable {path}: {str(e)}"
            
        return True, path
    except Exception as e:
        return False, f"Invalid path {path}: {str(e)}"

def get_images_path(config):
    """Get the images directory path based on configuration and environment"""
    # Check if custom path is specified in config
    if config.get('IMAGES_PATH'):
        # Handle both absolute and relative paths
        images_path = config['IMAGES_PATH']
        if not os.path.isabs(images_path):
            # Relative paths are relative to the executable/project root
            images_path = os.path.join(get_base_path(), images_path)
        
        # Validate the custom path
        is_valid, result = validate_images_path(images_path)
        if not is_valid:
            print(f"\nWarning: {result}")
            print("Falling back to default images path...")
        else:
            return result
    
    # Default paths
    if is_frozen():
        # In deployed mode, images folder is next to the executable
        default_path = os.path.join(get_base_path(), 'images')
    else:
        # In development mode, images folder is in the project directory
        default_path = os.path.join(get_base_path(), 'mini_photo_frame', 'images')
    
    # Validate default path
    is_valid, result = validate_images_path(default_path)
    if not is_valid:
        raise RuntimeError(f"Could not create or access default images directory: {result}")
    
    return result

def run_digital_picture_frame(folder_id, local_image_folder, service, settings):
    """Run the picture frame with the given settings"""
    # Initial sync
    new_photos, all_photos = sync_drive_images(service, folder_id, local_image_folder, settings)
    last_sync_time = time.time()
    last_settings_check = time.time()
    settings_check_interval = 60  # Check settings every minute
    
    # Track current position for back functionality
    current_index = 0
    photo_history = []
    photos_to_display = all_photos
    already_shown = set()  # Track which photos have been shown

    while True:
        current_time = time.time()
        settings_updated = False
        
        # Check for settings updates periodically
        if current_time - last_settings_check >= settings_check_interval:
            settings_folder_id = get_or_create_settings_folder(service, folder_id)
            # Ensure settings folders exist
            ensure_default_settings_folders(service, settings_folder_id, settings)
            # Get current settings
            new_settings, _ = get_settings_from_folders(service, settings_folder_id, settings)
            if new_settings != settings:
                print("\nSettings updated from Google Drive folders:")
                if new_settings['display_interval'] != settings['display_interval']:
                    print(f"Display interval: {new_settings['display_interval'] // 60} minutes")
                if new_settings['sync_interval'] != settings['sync_interval']:
                    print(f"Sync interval: {new_settings['sync_interval'] // 60} minutes")
                if new_settings['shuffle'] != settings['shuffle']:
                    print(f"Shuffle mode: {new_settings['shuffle']}")
                if new_settings.get('search') != settings.get('search'):
                    print(f"Search query updated: {new_settings.get('search', '(none)')}")
                    settings_updated = True
                settings.update(new_settings)
            last_settings_check = current_time

        # Check for new photos on interval or if settings were updated
        if settings_updated or current_time - last_sync_time >= settings['sync_interval']:
            print("Checking for new photos...")
            new_photos, all_photos = sync_drive_images(service, folder_id, local_image_folder, settings)
            last_sync_time = current_time
            if settings_updated:
                # If settings changed, reset everything
                photos_to_display = all_photos
                current_index = 0
                photo_history = []
                already_shown.clear()
            elif new_photos:
                # If just new photos, add them to the start but preserve current queue
                photos_to_display = new_photos + [p for p in photos_to_display if p not in new_photos]
                print(f"Added {len(new_photos)} new photos to the start of the queue")

        # Handle end of list
        if current_index >= len(photos_to_display):
            if settings['shuffle']:
                # When reshuffling, exclude photos we've already shown this cycle
                unshown_photos = [p for p in photos_to_display if p not in already_shown]
                if unshown_photos:
                    random.shuffle(unshown_photos)
                    photos_to_display = unshown_photos
                else:
                    # If all photos shown, start fresh
                    already_shown.clear()
                    photos_to_display = all_photos.copy()
                    random.shuffle(photos_to_display)
            else:
                # For non-shuffle mode, just start over
                photos_to_display = all_photos
                already_shown.clear()
            current_index = 0
            photo_history = []

        # Display current photo
        photo_name = photos_to_display[current_index]
        photo_path = os.path.join(local_image_folder, photo_name)
        if not os.path.exists(photo_path):
            current_index += 1
            continue
            
        print(f"Showing photo: {photo_name}")
        already_shown.add(photo_name)  # Mark this photo as shown
        action = show_photo(photo_path, settings['display_interval'])
        
        if action == "exit":
            return
        elif action == "reshuffle":
            already_shown.clear()  # Reset on manual reshuffle
            random.shuffle(photos_to_display)
            current_index = 0
            photo_history = []
            print("Reshuffling photos...")
        elif action == "new":
            # Force a sync check
            last_sync_time = 0
            last_settings_check = 0
        elif action == "back":
            if photo_history:
                current_index = photo_history.pop()
                if photos_to_display[current_index] in already_shown:
                    already_shown.remove(photos_to_display[current_index])
        else:  # "next" or any other key
            photo_history.append(current_index)
            if len(photo_history) > 50:  # Limit history size
                photo_history.pop(0)
            current_index += 1
            
            # Quick check for new photos on 'next'
            if current_time - last_sync_time >= 30:  # Only check if it's been at least 30 seconds
                temp_settings = settings.copy()
                temp_settings.pop('search', None)  # Remove search to preserve current order
                new_photos, _ = sync_drive_images(service, folder_id, local_image_folder, temp_settings)
                last_sync_time = current_time
                if new_photos:
                    # Add new photos to the front but preserve current queue
                    photos_to_display = new_photos + [p for p in photos_to_display if p not in new_photos]
                    print(f"Added {len(new_photos)} new photos to the start of the queue")

def main():
    # Load configuration
    config = load_config()
    
    if not config['FOLDER_ID'] or config['FOLDER_ID'] == 'your_google_drive_folder_id_here':
        print("\nPlease set your Google Drive folder ID in config.txt")
        if not is_frozen():
            print("Development mode: Edit config.txt in the project root.")
        return

    # Get the correct images path
    local_image_folder = get_images_path(config)
    print(f"\nUsing images directory: {local_image_folder}")
    
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
    settings, _ = get_settings_from_folders(service, settings_folder_id, settings)
    
    print("\nStarting photo frame with settings:")
    print(f"Display interval: {settings['display_interval'] // 60} minutes")
    print(f"Sync interval: {settings['sync_interval'] // 60} minutes")
    print(f"Shuffle mode: {settings['shuffle']}")
    
    run_digital_picture_frame(config['FOLDER_ID'], local_image_folder, service, settings)

if __name__ == "__main__":
    main()



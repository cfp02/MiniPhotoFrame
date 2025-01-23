import time
import os
import random
import sys
import pyautogui
from drive_auth import (
    authenticate_google_drive, 
    is_frozen, 
    get_base_path
)
import drive_manager
from drive_manager import (
    create_drive_service, download_photo,
    get_or_create_settings_folder, get_settings_from_folders,
    ensure_default_settings_folders, check_internet_connection
)
from display_manager import show_photo, show_photo_simple
from datetime import datetime, timedelta
import logging

def move_mouse_to_corner():
    """Move mouse to bottom right corner"""
    try:
        # Get screen size
        screen_width, screen_height = pyautogui.size()
        # Move to bottom right (subtract a few pixels to ensure it triggers corner)
        pyautogui.moveTo(screen_width - 1, screen_height - 1)
    except Exception as e:
        print(f"Could not move mouse: {str(e)}")

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

    # Get list of photos in Google Drive (sorted by creation time)
    new_photos, all_photos = drive_manager.sync_drive_images(service, folder_id, local_folder, settings)
    return new_photos, all_photos

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
    last_internet_check = 0
    internet_check_interval = 30  # Check internet every 30 seconds
    is_offline = not check_internet_connection()
    
    # Track current position for back functionality
    current_index = 0
    photo_history = []
    photos_to_display = all_photos
    already_shown = set()  # Track which photos have been shown

    # Get display function based on config
    display_func = show_photo_simple if settings.get('display_mode') == 'simple' else show_photo

    while True:
        current_time = time.time()
        settings_updated = False
        
        # Check internet connectivity periodically
        if current_time - last_internet_check >= internet_check_interval:
            was_offline = is_offline
            is_offline = not check_internet_connection()
            if was_offline and not is_offline:
                print("\nInternet connection restored. Resuming normal operation.")
                # Force a sync on reconnection
                last_sync_time = 0
                last_settings_check = 0
            elif not was_offline and is_offline:
                print("\nInternet connection lost. Operating in offline mode.")
            last_internet_check = current_time
        
        # Check for settings updates periodically
        if not is_offline and current_time - last_settings_check >= settings_check_interval:
            try:
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
            except Exception as e:
                print(f"\nError checking settings: {str(e)}")
                print("Continuing with current settings...")
            last_settings_check = current_time
            
        # Check for new photos on interval or if settings were updated
        if not is_offline and (settings_updated or current_time - last_sync_time >= settings['sync_interval']):
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
                # Insert new photos at current position
                photos_before = photos_to_display[:current_index]
                photos_after = photos_to_display[current_index:]
                photos_to_display = photos_before + new_photos + [p for p in photos_after if p not in new_photos]
                print(f"Added {len(new_photos)} new photos at current position in the queue")

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
        action = display_func(photo_path, settings['display_interval'], settings['rotation'])
        
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
                    # Insert new photos at current position
                    photos_before = photos_to_display[:current_index]
                    photos_after = photos_to_display[current_index:]
                    photos_to_display = photos_before + new_photos + [p for p in photos_after if p not in new_photos]
                    print(f"Added {len(new_photos)} new photos at current position in the queue")

def main():
    # Move mouse to corner at startup
    move_mouse_to_corner()
    
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
    
    # Initialize credentials and service regardless of internet status
    creds = authenticate_google_drive()
    if not creds:
        return
        
    service = create_drive_service(creds)
    if not service:
        return
    
    # Convert config to settings format
    settings = {
        'display_interval': config['DISPLAY_INTERVAL'],
        'sync_interval': config['SYNC_INTERVAL'],
        'shuffle': config.get('SHUFFLE', True),
        'filter': None,
        'display_mode': config.get('DISPLAY_MODE', 'original'),  # Default to original mode if not specified
        'rotation': int(config.get('ROTATION', '0'))  # Default to 0 if not specified
    }
    
    print(f"\nUsing display mode: {settings['display_mode']}")
    print(f"Image rotation: {settings['rotation']} degrees")
    
    # Check internet connectivity
    if not check_internet_connection():
        print("\nNo internet connection detected. Starting in offline mode...")
        # Get list of local photos
        local_photos = []
        for root, _, files in os.walk(local_image_folder):
            for file in files:
                if file != ".gitkeep":
                    rel_path = os.path.relpath(os.path.join(root, file), local_image_folder).replace('\\', '/')
                    local_photos.append(rel_path)
        
        if not local_photos:
            print("\nNo local photos found. Please ensure there are photos in the images directory.")
            return
            
        print(f"\nFound {len(local_photos)} local photos.")
        print("\nStarting photo frame with default settings:")
        print(f"Display interval: {settings['display_interval'] // 60} minutes")
        print(f"Shuffle mode: {settings['shuffle']}")
        
        # Start the photo frame with the service object (so it can recover when internet returns)
        run_digital_picture_frame(config['FOLDER_ID'], local_image_folder, service, settings)
        return
    
    # Online mode - proceed with normal startup
    print("\nInternet connection available. Starting in online mode...")
    
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



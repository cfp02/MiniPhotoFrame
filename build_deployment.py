import PyInstaller.__main__
import os
import shutil
import sys

def build_executable():
    # Get absolute paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    main_path = os.path.join(base_dir, 'mini_photo_frame', 'main.py')
    deployment_path = os.path.join(base_dir, 'deployment')
    
    # Verify main.py exists
    if not os.path.exists(main_path):
        print(f"Error: Cannot find {main_path}")
        return
        
    print(f"Building from: {main_path}")
    print(f"Deployment path: {deployment_path}")
    
    # Get the correct extension for the executable based on the platform
    exe_extension = '.exe' if sys.platform == 'win32' else ''
    
    # Create deployment directory structure
    if os.path.exists(deployment_path):
        # Don't delete the entire deployment folder, just clean up non-essential files
        for item in os.listdir(deployment_path):
            item_path = os.path.join(deployment_path, item)
            if item != 'images' and item != 'service_account':  # Preserve these directories
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
    else:
        os.makedirs(deployment_path)
    
    # Ensure service_account directory exists
    os.makedirs(os.path.join(deployment_path, 'service_account'), exist_ok=True)
    
    # PyInstaller configuration
    PyInstaller.__main__.run([
        main_path,
        '--onefile',
        '--name=photo_frame',
        f'--distpath={deployment_path}',
        '--clean',
    ])
    
    # Create README
    with open(os.path.join(deployment_path, 'README.txt'), 'w') as f:
        f.write(f"""Mini Photo Frame Deployment Package

Setup Instructions:
1. Copy this entire folder to your target machine
2. Place your Google Drive service account JSON file in the 'service_account' folder
3. Edit config.txt to set your Google Drive folder ID
4. (Optional) Set IMAGES_PATH in config.txt for persistent storage
5. Run the photo_frame{exe_extension} executable

Configuration:
1. Local config.txt file (basic settings):
   - Display interval: 45 minutes per photo
   - Sync interval: Checks for new photos every 5 minutes
   - Shuffle mode: On by default
   - Images path: Where to store downloaded photos

2. Google Drive settings (dynamic settings):
   The program will create a 'settings' folder in your Google Drive where
   you can change settings by creating/renaming folders:
   - display_interval_mins_45 (changes display time to 45 minutes)
   - sync_interval_mins_5 (changes sync interval to 5 minutes)
   - shuffle_true/shuffle_false (enables/disables shuffle)

Note: 
- Google Drive settings override local config.txt settings
- Set IMAGES_PATH in config.txt to keep photos between updates
- Default storage is in the 'images' folder next to the executable
""")

    # Create config file
    with open(os.path.join(deployment_path, 'config.txt'), 'w') as f:
        f.write("""# Configuration settings for Mini Photo Frame
# These are default settings that can be overridden by folders in Google Drive

# Your Google Drive folder ID (required)
# This is the long string of characters in the URL when you open your Google Drive folder
FOLDER_ID=your_google_drive_folder_id_here

# Display mode (simple or original)
# simple: Just shows photos centered with black borders
# original: Shows photos with captions and calculated borders (for bird photo frame)
DISPLAY_MODE=simple

# Display interval in seconds (45 minutes default)
# Can be overridden by creating a folder named 'display_interval_mins_45' in the settings folder
DISPLAY_INTERVAL=2700

# Sync interval in seconds (5 minutes default)
# Can be overridden by creating a folder named 'sync_interval_mins_5' in the settings folder
SYNC_INTERVAL=300

# Whether to shuffle photos after showing new ones
# Can be overridden by creating a folder named 'shuffle_true' or 'shuffle_false' in the settings folder
SHUFFLE=true

# Logging level (default: INFO)
# Available levels, from most to least verbose:
#   DEBUG   - Show all debug messages, very detailed logging
#   INFO    - Show general operation information (default)
#   WARNING - Show only warnings and errors
#   ERROR   - Show only errors
#   CRITICAL - Show only critical errors
LOG_LEVEL=INFO

# Path to store downloaded images (optional)
# If not specified, will use 'images' folder in the same directory as the executable
# Examples:
#   Windows: IMAGES_PATH=C:/PhotoFrame/images
#   Mac/Linux: IMAGES_PATH=/Users/username/PhotoFrame/images
#   Relative: IMAGES_PATH=../persistent_images
IMAGES_PATH=""")

    print(f"""
Deployment package created successfully!

To deploy:
1. Copy the entire 'deployment' folder to your target machine
2. Place your service account JSON file in the 'deployment/service_account' folder
3. Edit 'deployment/config.txt' to set your Google Drive folder ID
4. (Optional) Set IMAGES_PATH in config.txt for persistent storage
5. Run 'deployment/photo_frame{exe_extension}'
""")

if __name__ == "__main__":
    build_executable() 
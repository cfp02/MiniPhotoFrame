import PyInstaller.__main__
import os
import shutil
import sys

def build_executable():
    # Get the correct extension for the executable based on the platform
    exe_extension = '.exe' if sys.platform == 'win32' else ''
    
    # PyInstaller configuration
    PyInstaller.__main__.run([
        'mini_photo_frame/main.py',
        '--onefile',
        '--name=photo_frame',
        '--add-data=mini_photo_frame/images:images',
        '--distpath=deployment',  # Output directly to deployment folder
    ])

    # Create deployment directory structure
    os.makedirs('deployment/service_account', exist_ok=True)
    
    # Create README
    with open('deployment/README.txt', 'w') as f:
        f.write(f"""Mini Photo Frame Deployment Package

Setup Instructions:
1. Copy this entire folder to your target machine
2. Place your Google Drive service account JSON file in the 'service_account' folder
3. Edit config.txt to set your Google Drive folder ID
4. Run the photo_frame{exe_extension} executable

Configuration:
1. Local config.txt file (basic settings):
   - Display interval: 45 minutes per photo
   - Sync interval: Checks for new photos every 5 minutes
   - Shuffle mode: On by default

2. Google Drive settings (dynamic settings):
   The program will create a 'settings' folder in your Google Drive where
   you can change settings by creating/renaming folders:
   - display_interval_45 (changes display time to 45 minutes)
   - sync_interval_5 (changes sync interval to 5 minutes)
   - shuffle_true/shuffle_false (enables/disables shuffle)

Note: Google Drive settings override local config.txt settings.
""")

    # Create config file
    with open('deployment/config.txt', 'w') as f:
        f.write("""# Configuration settings for Mini Photo Frame
# These are default settings that can be overridden by folders in Google Drive

# Your Google Drive folder ID (required)
# This is the long string of characters in the URL when you open your Google Drive folder
FOLDER_ID=your_google_drive_folder_id_here

# Display interval in seconds (45 minutes default)
# Can be overridden by creating a folder named 'display_interval_45' in the settings folder
DISPLAY_INTERVAL=2700

# Sync interval in seconds (5 minutes default)
# Can be overridden by creating a folder named 'sync_interval_5' in the settings folder
SYNC_INTERVAL=300

# Whether to shuffle photos after showing new ones
# Can be overridden by creating a folder named 'shuffle_true' or 'shuffle_false' in the settings folder
SHUFFLE=true""")

    print(f"""
Deployment package created successfully!

To deploy:
1. Copy the entire 'deployment' folder to your target machine
2. Place your service account JSON file in the 'deployment/service_account' folder
3. Edit 'deployment/config.txt' to set your Google Drive folder ID
4. Run 'deployment/photo_frame{exe_extension}'
""")

if __name__ == "__main__":
    build_executable() 
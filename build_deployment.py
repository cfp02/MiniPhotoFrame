import PyInstaller.__main__
import os
import shutil

def build_executable():
    # PyInstaller configuration
    PyInstaller.__main__.run([
        'mini_photo_frame/main.py',
        '--onefile',
        '--name=photo_frame',
        '--add-data=mini_photo_frame/images:images',
    ])

    # Create deployment directory
    if os.path.exists('deployment'):
        shutil.rmtree('deployment')
    os.makedirs('deployment')
    os.makedirs('deployment/service_account')

    # Copy executable
    shutil.copy2('dist/photo_frame', 'deployment/')

    # Create README
    with open('deployment/README.txt', 'w') as f:
        f.write("""Mini Photo Frame Deployment Package

Setup Instructions:
1. Place your Google Drive service account JSON file in the 'service_account' folder
2. Run the photo_frame executable
3. The program will use the service account to access your Google Drive photos

Configuration:
- Display interval: 45 minutes per photo
- Sync interval: Checks for new photos every 5 minutes
- Photos are shown newest first, then randomly

To change these settings, edit the config.txt file.
""")

    # Create config file
    with open('deployment/config.txt', 'w') as f:
        f.write("""# Configuration settings for Mini Photo Frame
# These are default settings that can be overridden by folders in Google Drive

# Your Google Drive folder ID (required)
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

if __name__ == "__main__":
    build_executable() 
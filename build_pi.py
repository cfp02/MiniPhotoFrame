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
    
    # PyInstaller configuration optimized for Pi Zero
    PyInstaller.__main__.run([
        main_path,
        '--onefile',
        '--name=photo_frame',
        f'--distpath={deployment_path}',
        '--clean',
        '--noupx',  # UPX can cause issues on ARM
        '--hidden-import=PIL._tkinter',  # Required for Pillow
        '--hidden-import=google.auth.transport.requests',  # Required for Google Auth
        '--hidden-import=google.oauth2.credentials',  # Required for Google Auth
        '--hidden-import=google_auth_oauthlib.flow',  # Required for Google Auth
    ])
    
    # Create README
    with open(os.path.join(deployment_path, 'README.txt'), 'w') as f:
        f.write("""Mini Photo Frame Deployment Package for Raspberry Pi

Setup Instructions:
1. Run install_dependencies.sh to install required system packages
2. Place your Google Drive service account JSON file in the 'service_account' folder
3. Edit config.txt to set your Google Drive folder ID
4. Run the photo_frame executable

To run at startup:
1. Create an autostart entry:
   mkdir -p ~/.config/autostart
   nano ~/.config/autostart/photoframe.desktop

2. Add the following content:
   [Desktop Entry]
   Type=Application
   Name=Photo Frame
   Exec=/path/to/photo_frame
   Hidden=false
   X-GNOME-Autostart-enabled=true

3. Make the file executable:
   chmod +x ~/.config/autostart/photoframe.desktop

Note: 
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
# original: Shows photos with captions and calculated borders
DISPLAY_MODE=simple

# Image rotation in degrees (0, 90, 180, or 270)
# Use this to adjust the orientation of all photos:
#   0   - Normal orientation
#   90  - Rotate 90 degrees clockwise
#   180 - Upside down
#   270 - Rotate 90 degrees counterclockwise
ROTATION=0

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
IMAGES_PATH=""")

    print("""
Deployment package created successfully!

To deploy to Raspberry Pi Zero:
1. Copy the entire 'deployment' folder to your Pi
2. Run install_dependencies.sh to install required packages
3. Place your service account JSON file in the 'deployment/service_account' folder
4. Edit 'deployment/config.txt' to set your Google Drive folder ID
5. Run 'deployment/photo_frame'
""")

if __name__ == "__main__":
    build_executable() 
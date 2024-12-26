# drive_manager.py
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import googleapiclient.http
import io
import logging

# Set up logging
logger = logging.getLogger(__name__)

def create_drive_service(creds):
    return build('drive', 'v3', credentials=creds)

def upload_photo(service, file_path, folder_id=None):
    file_metadata = {'name': os.path.basename(file_path)}
    if folder_id:
        file_metadata['parents'] = [folder_id]
    media = MediaFileUpload(file_path, mimetype='image/jpeg')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f'Uploaded file with ID: {file.get("id")}')
    return file.get('id')

def sanitize_path(name):
    """Sanitize folder/file names to be safe for filesystem"""
    # Replace slashes with underscores to prevent path manipulation
    name = name.replace('/', '_').replace('\\', '_')
    # Replace any other potentially problematic characters
    # but keep spaces and periods as they're handled fine by os.path
    return name

def list_photos(service, folder_id=None):
    """List all photos in the given folder and its subfolders, excluding the settings folder"""
    photos = []
    
    def get_items_in_folder(folder_id):
        # Query for both images and folders in this directory
        query = f"'{folder_id}' in parents and (mimeType='image/jpeg' or mimeType='application/vnd.google-apps.folder')"
        results = service.files().list(
            q=query,
            spaces='drive',
            fields="files(id, name, mimeType, createdTime)",
            orderBy="createdTime desc"
        ).execute()
        return results.get('files', [])
    
    def process_folder(folder_id, current_path=""):
        items = get_items_in_folder(folder_id)
        for item in items:
            # Sanitize the item name
            safe_name = sanitize_path(item['name'])
            
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                if item['name'].lower() != 'settings':
                    # Recursively process subfolders with updated path
                    subfolder_path = os.path.join(current_path, safe_name)
                    process_folder(item['id'], subfolder_path)
            else:  # It's an image
                # Add path information to the photo
                item['path'] = os.path.join(current_path, safe_name)
                photos.append(item)
    
    # Start the recursive process from the root folder
    process_folder(folder_id)
    return photos

def download_photo(service, photo, local_path):
    """Download a photo from Drive to local storage
    
    Args:
        service: Google Drive service instance
        photo: Either a dict with 'id', 'name', and 'path' keys, or a string file ID
        local_path: Base path where to store the downloaded file
    """
    try:
        # Handle case where photo is just a file ID string
        if isinstance(photo, str):
            file_id = photo
            file_metadata = service.files().get(fileId=file_id, fields='name').execute()
            file_name = file_metadata['name']
            file_path = os.path.join(local_path, sanitize_path(file_name))
        else:
            # Ensure photo has required fields
            if not all(key in photo for key in ['id', 'path']):
                raise ValueError("Photo dict missing required fields ('id', 'path')")
            file_id = photo['id']
            file_path = os.path.join(local_path, photo['path'])

        # Ensure the directory exists
        photo_dir = os.path.dirname(file_path)
        os.makedirs(photo_dir, exist_ok=True)
        
        # Download the file
        request = service.files().get_media(fileId=file_id)
        
        # Stream the file to disk
        with io.BytesIO() as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            fh.seek(0)
            
            # Save the file
            with open(file_path, 'wb') as f:
                f.write(fh.read())
        
        return file_path
    except Exception as e:
        logger.error(f"Error downloading photo: {str(e)}")
        return None

def create_folder(service, folder_name, parent_id=None):
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        file_metadata['parents'] = [parent_id]
    
    folder = service.files().create(body=file_metadata, fields='id').execute()
    return folder.get('id')

def get_or_create_settings_folder(service, parent_folder_id):
    """Get or create the settings folder and return its ID"""
    query = f"mimeType='application/vnd.google-apps.folder' and name='settings' and '{parent_folder_id}' in parents"
    results = service.files().list(q=query, spaces='drive', fields="files(id)").execute()
    folders = results.get('files', [])
    
    if folders:
        return folders[0]['id']
    else:
        return create_folder(service, 'settings', parent_folder_id)

def get_settings_from_folders(service, settings_folder_id, default_settings):
    """Read settings from folder names in the settings folder"""
    settings = default_settings.copy()
    
    # List all folders in settings
    query = f"mimeType='application/vnd.google-apps.folder' and '{settings_folder_id}' in parents"
    results = service.files().list(q=query, spaces='drive', fields="files(name)").execute()
    folders = results.get('files', [])
    
    # Track which settings have been found
    found_settings = set()
    
    # Parse folder names for settings
    for folder in folders:
        name = folder['name'].lower()
        try:
            if name.startswith('display_interval_mins_'):
                value = int(name.split('_')[-1]) * 60  # Convert minutes to seconds
                settings['display_interval'] = value
                found_settings.add('display_interval')
            elif name.startswith('sync_interval_mins_'):
                value = int(name.split('_')[-1]) * 60  # Convert minutes to seconds
                settings['sync_interval'] = value
                found_settings.add('sync_interval')
            elif name.startswith('shuffle_'):
                settings['shuffle'] = name.split('_')[-1].lower() == 'true'
                found_settings.add('shuffle')
            elif name.startswith('filter_'):
                settings['filter'] = name[7:]  # Remove 'filter_' prefix
                found_settings.add('filter')
        except ValueError:
            continue
    
    return settings, found_settings

def ensure_default_settings_folders(service, settings_folder_id, default_settings):
    """Create default settings folders if they don't exist and no custom ones are present"""
    # First, get current settings and which ones were found
    _, found_settings = get_settings_from_folders(service, settings_folder_id, default_settings)
    
    # Only create default folders for settings that don't have any folders yet
    default_folders = []
    
    if 'display_interval' not in found_settings:
        display_mins = default_settings['display_interval'] // 60
        default_folders.append(f'display_interval_mins_{display_mins}')
    
    if 'sync_interval' not in found_settings:
        sync_mins = default_settings['sync_interval'] // 60
        default_folders.append(f'sync_interval_mins_{sync_mins}')
    
    if 'shuffle' not in found_settings:
        default_folders.append(f'shuffle_{str(default_settings["shuffle"]).lower()}')
    
    # Check existing folders to avoid duplicates
    query = f"mimeType='application/vnd.google-apps.folder' and '{settings_folder_id}' in parents"
    results = service.files().list(q=query, spaces='drive', fields="files(name)").execute()
    existing_folders = set(folder['name'].lower() for folder in results.get('files', []))
    
    # Create missing folders
    for folder_name in default_folders:
        if folder_name.lower() not in existing_folders:
            create_folder(service, folder_name, settings_folder_id)
            print(f"Created default settings folder: {folder_name}")

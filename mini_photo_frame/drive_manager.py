# drive_manager.py
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import googleapiclient.http
import io
import logging

# Set up logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def create_drive_service(creds):
    logger.info("Creating Google Drive service...")
    try:
        service = build('drive', 'v3', credentials=creds)
        logger.info("Successfully created Google Drive service")
        return service
    except Exception as e:
        logger.error(f"Failed to create Drive service: {str(e)}")
        raise

def upload_photo(service, file_path, folder_id=None):
    logger.info(f"Uploading photo: {file_path}")
    try:
        file_metadata = {'name': os.path.basename(file_path)}
        if folder_id:
            file_metadata['parents'] = [folder_id]
            logger.info(f"Uploading to folder ID: {folder_id}")
        
        media = MediaFileUpload(file_path, mimetype='image/jpeg')
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        logger.info(f'Successfully uploaded file with ID: {file.get("id")}')
        return file.get('id')
    except Exception as e:
        logger.error(f"Failed to upload photo {file_path}: {str(e)}")
        raise

def sanitize_path(name):
    """Sanitize folder/file names to be safe for filesystem"""
    # Replace slashes with underscores to prevent path manipulation
    name = name.replace('/', '_').replace('\\', '_')
    # Replace any other potentially problematic characters
    # but keep spaces and periods as they're handled fine by os.path
    return name

def list_photos(service, folder_id=None):
    """List all photos in the given folder and its subfolders, excluding the settings folder"""
    logger.info(f"Listing photos from folder ID: {folder_id}")
    photos = []
    
    def get_items_in_folder(folder_id):
        logger.debug(f"Fetching items from folder: {folder_id}")
        query = f"'{folder_id}' in parents and (mimeType='image/jpeg' or mimeType='application/vnd.google-apps.folder')"
        try:
            results = service.files().list(
                q=query,
                spaces='drive',
                fields="files(id, name, mimeType, createdTime)",
                orderBy="createdTime desc"
            ).execute()
            items = results.get('files', [])
            logger.debug(f"Found {len(items)} items in folder {folder_id}")
            return items
        except Exception as e:
            logger.error(f"Error fetching items from folder {folder_id}: {str(e)}")
            return []
    
    def process_folder(folder_id, current_path=""):
        items = get_items_in_folder(folder_id)
        for item in items:
            safe_name = sanitize_path(item['name'])
            
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                if item['name'].lower() != 'settings':
                    logger.debug(f"Processing subfolder: {safe_name}")
                    # For folders, just append the folder name to the current path
                    subfolder_path = os.path.join(current_path, safe_name) if current_path else safe_name
                    process_folder(item['id'], subfolder_path)
                else:
                    logger.debug("Skipping settings folder")
            else:
                # Store both the full path and the filename separately
                item['filename'] = safe_name
                item['path'] = os.path.join(current_path, safe_name) if current_path else safe_name
                item['directory'] = current_path  # Store the directory path separately
                logger.debug(f"Found photo: {item['path']}")
                photos.append(item)
    
    process_folder(folder_id)
    logger.info(f"Found total of {len(photos)} photos")
    return photos

def download_photo(service, photo, local_path):
    """Download a photo from Drive to local storage"""
    try:
        if isinstance(photo, str):
            file_id = photo
            logger.info(f"Downloading photo with ID: {file_id}")
            file_metadata = service.files().get(fileId=file_id, fields='name').execute()
            file_name = sanitize_path(file_metadata['name'])
            file_path = os.path.join(local_path, file_name)
            logger.debug(f"Single file will be saved as: {file_path}")
        else:
            if not all(key in photo for key in ['id', 'path']):
                error_msg = "Photo dict missing required fields ('id', 'path')"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            file_id = photo['id']
            # Use the path directly as it's already properly constructed
            file_path = local_path # os.path.join(local_path, photo['path'])
            logger.info(f"Downloading photo to: {file_path} (ID: {file_id})")

        # Create the directory structure if needed
        dir_path = os.path.dirname(file_path)
        if dir_path:
            try:
                os.makedirs(dir_path, exist_ok=True)
                logger.debug(f"Created/verified directory structure: {dir_path}")
            except Exception as e:
                logger.error(f"Failed to create directory structure {dir_path}: {str(e)}")
                return None
        
        # Download the file
        request = service.files().get_media(fileId=file_id)
        
        # Stream the file to disk
        with io.BytesIO() as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                logger.debug(f"Download progress: {int(status.progress() * 100)}%")
            fh.seek(0)
            
            # Write the file
            try:
                with open(file_path, 'wb') as f:
                    f.write(fh.read())
                logger.info(f"Successfully downloaded photo to: {file_path}")
                return file_path
            except Exception as e:
                logger.error(f"Failed to write file {file_path}: {str(e)}")
                return None
                
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
    logger.info("Looking for settings folder...")
    try:
        query = f"mimeType='application/vnd.google-apps.folder' and name='settings' and '{parent_folder_id}' in parents"
        results = service.files().list(q=query, spaces='drive', fields="files(id)").execute()
        folders = results.get('files', [])
        
        if folders:
            folder_id = folders[0]['id']
            logger.info(f"Found existing settings folder: {folder_id}")
            return folder_id
        else:
            logger.info("Settings folder not found, creating new one...")
            folder_id = create_folder(service, 'settings', parent_folder_id)
            logger.info(f"Created new settings folder: {folder_id}")
            return folder_id
    except Exception as e:
        logger.error(f"Error accessing settings folder: {str(e)}")
        raise

def get_settings_from_folders(service, settings_folder_id, default_settings):
    """Read settings from folder names in the settings folder"""
    logger.info("Reading settings from folder names...")
    settings = default_settings.copy()
    
    try:
        query = f"mimeType='application/vnd.google-apps.folder' and '{settings_folder_id}' in parents"
        results = service.files().list(q=query, spaces='drive', fields="files(name)").execute()
        folders = results.get('files', [])
        logger.info(f"Found {len(folders)} settings folders")
        
        found_settings = set()
        
        for folder in folders:
            name = folder['name'].lower()
            try:
                if name.startswith('display_interval_mins_'):
                    value = int(name.split('_')[-1]) * 60
                    settings['display_interval'] = value
                    found_settings.add('display_interval')
                    logger.debug(f"Found display interval setting: {value} seconds")
                elif name.startswith('sync_interval_mins_'):
                    value = int(name.split('_')[-1]) * 60
                    settings['sync_interval'] = value
                    found_settings.add('sync_interval')
                    logger.debug(f"Found sync interval setting: {value} seconds")
                elif name.startswith('shuffle_'):
                    settings['shuffle'] = name.split('_')[-1].lower() == 'true'
                    found_settings.add('shuffle')
                    logger.debug(f"Found shuffle setting: {settings['shuffle']}")
                elif name.startswith('filter_'):
                    settings['filter'] = name[7:]
                    found_settings.add('filter')
                    logger.debug(f"Found filter setting: {settings['filter']}")
            except ValueError as e:
                logger.warning(f"Invalid setting folder name: {name} - {str(e)}")
                continue
        
        logger.info("Finished reading settings")
        logger.debug(f"Final settings: {settings}")
        return settings, found_settings
    except Exception as e:
        logger.error(f"Error reading settings: {str(e)}")
        raise

def ensure_default_settings_folders(service, settings_folder_id, default_settings):
    """Create default settings folders if they don't exist and no custom ones are present"""
    logger.info("Checking for missing default settings folders...")
    
    # First, get current settings and which ones were found
    _, found_settings = get_settings_from_folders(service, settings_folder_id, default_settings)
    
    # Only create default folders for settings that don't have any folders yet
    default_folders = []
    
    if 'display_interval' not in found_settings:
        display_mins = default_settings['display_interval'] // 60
        default_folders.append(f'display_interval_mins_{display_mins}')
        logger.debug(f"Need to create display interval folder: {display_mins} minutes")
    
    if 'sync_interval' not in found_settings:
        sync_mins = default_settings['sync_interval'] // 60
        default_folders.append(f'sync_interval_mins_{sync_mins}')
        logger.debug(f"Need to create sync interval folder: {sync_mins} minutes")
    
    if 'shuffle' not in found_settings:
        shuffle_value = str(default_settings["shuffle"]).lower()
        default_folders.append(f'shuffle_{shuffle_value}')
        logger.debug(f"Need to create shuffle folder: {shuffle_value}")
    
    if not default_folders:
        logger.info("All default settings folders already exist")
        return
    
    # Check existing folders to avoid duplicates
    try:
        query = f"mimeType='application/vnd.google-apps.folder' and '{settings_folder_id}' in parents"
        results = service.files().list(q=query, spaces='drive', fields="files(name)").execute()
        existing_folders = set(folder['name'].lower() for folder in results.get('files', []))
        
        # Create missing folders
        for folder_name in default_folders:
            if folder_name.lower() not in existing_folders:
                logger.info(f"Creating default settings folder: {folder_name}")
                try:
                    create_folder(service, folder_name, settings_folder_id)
                    logger.info(f"Successfully created settings folder: {folder_name}")
                except Exception as e:
                    logger.error(f"Failed to create settings folder {folder_name}: {str(e)}")
            else:
                logger.debug(f"Settings folder already exists: {folder_name}")
    except Exception as e:
        logger.error(f"Error ensuring default settings folders: {str(e)}")
        raise

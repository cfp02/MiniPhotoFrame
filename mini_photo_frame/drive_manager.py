# drive_manager.py
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import googleapiclient.http
import io
import logging
import random
import socket

# Set up logging with more detailed format
logging.basicConfig(
    level=logging.DEBUG,
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

def list_photos(service, folder_id=None, search_query=None, shuffle_enabled=False):
    """List all photos in the given folder and its subfolders, excluding the settings folder"""
    logger.info(f"Listing photos from folder ID: {folder_id}")
    if search_query:
        logger.info(f"Active search query: '{search_query}'")
    photos = []
    search_matches = []  # Track photos that match the search query
    
    def get_items_in_folder(folder_id):
        logger.debug(f"Fetching items from folder: {folder_id}")
        query = f"'{folder_id}' in parents and (mimeType='image/jpeg' or mimeType='application/vnd.google-apps.folder')"
        items = []
        page_token = None
        
        try:
            while True:
                results = service.files().list(
                    q=query,
                    spaces='drive',
                    fields="nextPageToken, files(id, name, mimeType, createdTime, description)",
                    orderBy="createdTime desc",  # Most recent first
                    pageToken=page_token,
                    pageSize=1000
                ).execute()
                
                batch_items = results.get('files', [])
                items.extend(batch_items)
                logger.debug(f"Fetched {len(batch_items)} items in this batch")
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                
            logger.debug(f"Found total of {len(items)} items in folder {folder_id}")
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
                    subfolder_path = os.path.join(current_path, safe_name) if current_path else safe_name
                    process_folder(item['id'], subfolder_path)
                else:
                    logger.debug("Skipping settings folder")
            else:
                # Store both the full path and the filename separately
                item['filename'] = safe_name
                item['path'] = os.path.join(current_path, safe_name) if current_path else safe_name
                item['directory'] = current_path
                
                # Check if photo matches search query
                if search_query:
                    description = item.get('description', '').lower()
                    name = item['name'].lower()
                    path = item['path'].lower()
                    if (search_query in description) or (search_query in name) or (search_query in path):
                        logger.info(f"Search match found: '{search_query}' in {item['path']}")
                        search_matches.append(item)
                
                logger.debug(f"Found photo: {item['path']}")
                photos.append(item)
    
    process_folder(folder_id)
    
    # Sort photos by creation time (newest first)
    photos.sort(key=lambda x: x.get('createdTime', ''), reverse=True)
    
    # If there's a search query, handle the search matches
    if search_query and search_matches:
        # Remove matching photos from main list to avoid duplicates
        photos = [p for p in photos if p not in search_matches]
        
        # If shuffle is enabled, shuffle the search matches
        if shuffle_enabled:
            random.shuffle(search_matches)
            logger.info("Shuffling search matches")
        else:
            # Sort search matches by creation time if not shuffling
            search_matches.sort(key=lambda x: x.get('createdTime', ''), reverse=True)
            logger.info("Sorting search matches by creation time")
        
        # Add search matches after any new photos but before the rest
        photos = search_matches + photos
        logger.info(f"Search results: {len(search_matches)} photos match '{search_query}', reordering them to show after new photos")
    elif search_query:
        logger.info(f"No photos found matching search query: '{search_query}'")
    
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
            file_path = local_path #os.path.join(local_path, file_name)
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
        has_search = False  # Track if we find a search folder
        
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
                elif name.startswith('search_'):
                    # Extract search query from folder name
                    search_query = name[7:]  # Remove 'search_' prefix
                    if search_query:  # Only set if not empty
                        settings['search'] = search_query
                        found_settings.add('search')
                        has_search = True
                        logger.info(f"Found search setting: '{search_query}'")
                elif name.startswith('filter_'):
                    settings['filter'] = name[7:]
                    found_settings.add('filter')
                    logger.debug(f"Found filter setting: {settings['filter']}")
            except ValueError as e:
                logger.warning(f"Invalid setting folder name: {name} - {str(e)}")
                continue
        
        if not has_search and 'search' in settings:
            logger.info("Search folder removed, clearing search setting")
            settings.pop('search', None)
        
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

def check_internet_connection():
    """Check if there is an active internet connection"""
    try:
        # Try to connect to Google's DNS server
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False

def sync_drive_images(service, folder_id, local_folder, settings=None):
    """Syncs images and returns a list of any new photos downloaded"""
    # Handle offline mode (service is None) or no internet connection
    if service is None or not check_internet_connection():
        logger.warning("Operating in offline mode. Using local photos only.")
        # Return empty list for new photos and list of all local photos
        local_photos = []
        for root, _, files in os.walk(local_folder):
            for file in files:
                if file != ".gitkeep":
                    rel_path = os.path.relpath(os.path.join(root, file), local_folder).replace('\\', '/')
                    local_photos.append(rel_path)
        return [], sorted(local_photos)  # Sort to maintain consistent order

    # Online mode - proceed with normal sync
    try:
        # Ensure the local folder exists
        if not os.path.exists(local_folder):
            os.makedirs(local_folder)

        # Step 1: Get list of photos in Google Drive (sorted by creation time)
        search_query = settings.get('search', '').lower() if settings else None
        shuffle_enabled = settings.get('shuffle', False) if settings else False
        drive_photos = list_photos(service, folder_id, search_query, shuffle_enabled)
        
        if not drive_photos:
            logger.warning("No photos found in Google Drive or unable to fetch list. Preserving local photos.")
            # If we can't get the drive photos list, just return local photos without deleting anything
            local_photos = []
            for root, _, files in os.walk(local_folder):
                for file in files:
                    if file != ".gitkeep":
                        rel_path = os.path.relpath(os.path.join(root, file), local_folder).replace('\\', '/')
                        local_photos.append(rel_path)
            return [], sorted(local_photos)
        
        # Create a map of photo IDs to their full info
        drive_photo_ids = {photo['id']: photo for photo in drive_photos}
        
        # Get set of all photo paths (normalized)
        drive_photo_paths = {photo['path'].replace('\\', '/') for photo in drive_photos}
        local_photos = {}  # Map of relative paths to full local paths
        
        logger.info("Scanning local files...")
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
                logger.info(f"Downloaded new photo: {rel_path}")
                new_photos.append(rel_path)
        
        # Only remove local photos if we successfully got the drive photos list
        photos_to_delete = set(local_photos.keys()) - drive_photo_paths
        if photos_to_delete:
            logger.info(f"\nRemoving {len(photos_to_delete)} photos that no longer exist in Drive:")
            for rel_path in photos_to_delete:
                logger.info(f"  Deleting: {rel_path}")
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
                    logger.error(f"  Error deleting {rel_path}: {str(e)}")
        
        # Return paths for all photos, with new ones first
        all_paths = [p['path'] for p in drive_photos]
        if new_photos:
            # Remove new photos from all_paths to avoid duplicates
            all_paths = [p for p in all_paths if p not in new_photos]
            # Add new photos at the start
            all_paths = new_photos + all_paths
        
        return new_photos, all_paths
        
    except Exception as e:
        logger.error(f"Error during sync: {str(e)}")
        logger.warning("Falling back to local photos only")
        # If anything goes wrong, just return local photos without deleting anything
        local_photos = []
        for root, _, files in os.walk(local_folder):
            for file in files:
                if file != ".gitkeep":
                    rel_path = os.path.relpath(os.path.join(root, file), local_folder).replace('\\', '/')
                    local_photos.append(rel_path)
        return [], sorted(local_photos)

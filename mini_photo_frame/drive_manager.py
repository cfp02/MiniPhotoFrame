# drive_manager.py
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import googleapiclient.http

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

def list_photos(service, folder_id=None):
    query = "mimeType='image/jpeg'"
    if folder_id:
        query += f" and '{folder_id}' in parents"
    results = service.files().list(
        q=query,
        spaces='drive',
        fields="nextPageToken, files(id, name, createdTime)",
        orderBy="createdTime desc"
    ).execute()
    return results.get('files', [])

def download_photo(service, file_id, file_name):
    request = service.files().get_media(fileId=file_id)
    with open(file_name, 'wb') as file:
        downloader = googleapiclient.http.MediaIoBaseDownload(file, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            print(f"Download {int(status.progress() * 100)}%.")

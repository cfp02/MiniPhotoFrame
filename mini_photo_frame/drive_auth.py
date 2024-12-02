# drive_auth.py
import os
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive']

def is_frozen():
    """Check if we're running in a PyInstaller bundle"""
    return getattr(sys, 'frozen', False)

def get_base_path():
    """Get the base path for the application, works in both dev and deployed modes"""
    if is_frozen():
        # Running in a bundle (deployed mode)
        return os.path.dirname(sys.executable)
    else:
        # Running in normal Python environment
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_service_account_path():
    """Get the service account directory path based on environment"""
    if is_frozen():
        # In deployed mode, service_account is next to the executable
        return os.path.join(get_base_path(), 'service_account')
    else:
        # In development mode, service_account is in the project root
        return os.path.join(get_base_path(), 'service_account')

def authenticate_google_drive():
    # Get the correct service account directory path
    service_account_path = get_service_account_path()
    
    # Create service_account directory if it doesn't exist
    if not os.path.exists(service_account_path):
        os.makedirs(service_account_path)
        print(f"\nNo service account directory found.")
        print(f"Created service account directory at: {service_account_path}")
        print("Please place your service account JSON file in this directory.")
        if not is_frozen():
            print("\nDevelopment mode instructions:")
            print("1. Get your service account JSON from Google Cloud Console")
            print("2. Place it in the 'service_account' folder in your project root")
        return None

    # Find JSON file in service_account directory
    json_files = [f for f in os.listdir(service_account_path) if f.endswith('.json')]
    
    if not json_files:
        print("\nNo service account JSON file found.")
        print(f"Please place your service account JSON file in: {service_account_path}")
        if not is_frozen():
            print("\nDevelopment mode instructions:")
            print("1. Get your service account JSON from Google Cloud Console")
            print("2. Place it in the 'service_account' folder in your project root")
        return None
    
    # Use the first JSON file found
    service_acct_json = os.path.join(service_account_path, json_files[0])
    
    try:
        creds = service_account.Credentials.from_service_account_file(
            service_acct_json, scopes=SCOPES)
        return creds
    except Exception as e:
        print(f"\nError loading service account credentials: {e}")
        print(f"Please check that your service account JSON file is valid.")
        return None

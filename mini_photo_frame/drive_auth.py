# drive_auth.py
import os
# import pickle
# from google.auth.transport.requests import Request
# from google.oauth2.credentials import Credentials
# from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive']  # Allows access to Google Drive

# def authenticate_google_drive():
#     creds = None
#     if os.path.exists('token.pickle'):
#         with open('token.pickle', 'rb') as token:
#             creds = pickle.load(token)
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             current_dir = os.path.dirname(os.path.abspath(__file__))
#             client_secret = os.path.join(current_dir, 'client_secret', 'client_secret.json')
#             print(client_secret)
#             flow = InstalledAppFlow.from_client_secrets_file(client_secret, SCOPES)
#             creds = flow.run_local_server(port=0)
#         with open('token.pickle', 'wb') as token:
#             pickle.dump(creds, token)
#     return creds

# drive_auth.py


SCOPES = ['https://www.googleapis.com/auth/drive']

def authenticate_google_drive():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    service_account_path = os.path.join(current_dir, 'service_account')
    # Get the file name of the service account JSON file, which should be the only file that ends in .json. There will be a text file in the service_account directory that you should ignore.
    json_filename = ''
    for file in os.listdir(service_account_path):
        if file.endswith('.json'):
            json_filename = file
            break
    try:
        service_acct_json = os.path.join(current_dir, 'service_account', json_filename)
    except FileNotFoundError:
        print('The service account JSON file was not found in the service_account directory.')
        return None
    creds = service_account.Credentials.from_service_account_file(
        service_acct_json, scopes=SCOPES)
    return creds

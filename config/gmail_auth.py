# config/gmail_auth.py
import os
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.freebusy",
]

def get_valid_credentials():
    """Handles authentication and returns valid OAuth2 credentials."""
    creds = None
    if os.path.exists('config/token.json'):
        creds = Credentials.from_authorized_user_file('config/token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('config/credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('config/token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def verify_gmail_connection():
    """Returns a Gmail API service client."""
    creds = get_valid_credentials()
    service = build('gmail', 'v1', credentials=creds)
    import sys

    print("Successfully connected to Gmail API!", file=sys.stderr)
    return service

def verify_calendar_connection():
    """Returns a Google Calendar API service client."""
    creds = get_valid_credentials()
    service = build('calendar', 'v3', credentials=creds)
    # print("Successfully connected to Google Calendar API!")
    
    print("Successfully connected to Google Calendar API!", file=sys.stderr)
    return service

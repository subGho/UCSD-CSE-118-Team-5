#!/usr/bin/env python3
"""
Fetch today's upcoming Google Calendar events and collect their summaries
into an array of strings.

Prereqs (same as Google Calendar Python quickstart):
- Create OAuth client credentials and save as credentials.json in this folder.
- On first run, a browser flow will create token.json.
- pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
"""

import datetime
import os.path
from typing import List

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Scope for read-only Calendar access
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def get_credentials() -> Credentials:
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds


def get_events_for_today(service) -> List[str]:
    now = datetime.datetime.now(datetime.timezone.utc)
    start_of_day = now.astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + datetime.timedelta(days=1)

    iso_start = start_of_day.isoformat()
    iso_end = end_of_day.isoformat()

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=iso_start,
            timeMax=iso_end,
            maxResults=50,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])

    summaries = []
    for event in events:
        summary = event.get("summary", "(No title)")
        start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
        summaries.append(f"{start}: {summary}")
    return summaries


def main():
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)
    summaries = get_events_for_today(service)
    print("Today's events:")
    for line in summaries:
        print(f"- {line}")


if __name__ == "__main__":
    main()

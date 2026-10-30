import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# 1. ផ្ទុក API Key ពី .env
load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")

if not API_KEY:
    raise ValueError("រកមិនឃើញ YOUTUBE_API_KEY ក្នុង .env ទេ")

try:
    # 2. បង្កើត YouTube Service
    youtube = build("youtube", "v3", developerKey=API_KEY)

    # 3. ទាញយកព័ត៌មាន Channel តាម Handle
    request = youtube.channels().list(
        part="snippet,statistics",
        forHandle="@haisokhompreapsovathmyidol1281"
    )

    response = request.execute()

    # 4. បង្ហាញលទ្ធផល
    if response.get("items"):
        channel = response["items"][0]

        title = channel["snippet"]["title"]
        channel_id = channel["id"]
        views = channel["statistics"]["viewCount"]
        subscribers = channel["statistics"].get("subscriberCount", "N/A")
        videos = channel["statistics"]["videoCount"]

        print("YouTube API ដំណើរការបានជោគជ័យ!")
        print(f"Channel Name: {title}")
        print(f"Channel ID: {channel_id}")
        print(f"Subscribers: {subscribers}")
        print(f"Total Views: {int(views):,}")
        print(f"Total Videos: {videos}")

    else:
        print("រកមិនឃើញ Channel នេះទេ")

except HttpError as e:
    print(f"YouTube API Error: {e}")

except Exception as e:
    print(f"Error: {e}")

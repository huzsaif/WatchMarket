import requests

def send_test_notification():
    api_url = "https://onesignal.com/api/v1/notifications"
    headers = {
        "Authorization": "os_v2_app_dtb3x2k4vjfrteifeqj6xntr7advhdoazo6e7bnmqfu7yp5qrsf6hqys35bodxrhibnx3amf6zniahjepvsobafptzy7oodx3v7zztq",  # Replace with your OneSignal API key
        "Content-Type": "application/json"
    }
    payload = {
        "app_id": "1cc3bbe9-5caa-4b19-9105-2413ebb671f8",  # Replace with your OneSignal App ID
        "included_segments": ["All"],
        "contents": {"en": "Test Notification: Rolex Explorer II Posted!"},
        "url": "https://www.reddit.com/r/Watchexchange/comments/example/"
    }

    response = requests.post(api_url, headers=headers, json=payload)
    print(f"Notification sent: {response.status_code}, {response.text}")

send_test_notification()
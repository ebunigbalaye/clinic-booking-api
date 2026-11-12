
import json
import time
import urllib.request
from pathlib import Path

BASE_URL = "https://clinic-booking-app-hrsx.onrender.com"
DEMO_EMAIL = "pagination.demo@example.com"


def read_api_key():
    for line in Path(".env").read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("API_KEY="):
            return line.split("=", 1)[1].strip().strip("\"'")

    raise ValueError("API_KEY not found in .env")


API_KEY = read_api_key()


def create_booking(slot_id, number):
    payload = {
        "slot_id": slot_id,
        "name": f"Pagination Demo Patient {number:02d}",
        "email": DEMO_EMAIL,
    }

    request = urllib.request.Request(
        f"{BASE_URL}/bookings",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    successful = 0

    for number, slot_number in enumerate(range(16, 27), start=1):
        slot_id = f"demo-{slot_number:03d}"

        print(f"Creating booking {number}/11 for {slot_id}...")

        try:
            result = create_booking(slot_id, number)
            successful += 1
            print(f"Success: {result}")

        except Exception as error:
            print(f"Failed: {error}")
            print("Stopping so we can investigate.")
            break

        if number < 11:
            print("Waiting 13 seconds to respect the rate limit...")
            time.sleep(13)

    print(f"\nCreated {successful} of 11 pagination bookings.")
    print(f"Demo email: {DEMO_EMAIL}")

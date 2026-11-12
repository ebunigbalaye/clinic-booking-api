
import json
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


BASE_URL = "https://clinic-booking-app-hrsx.onrender.com"
TIMEZONE = ZoneInfo("Africa/Lagos")

PROVIDERS = [
    "Dr. Ada Okafor",
    "Dr. David Bello",
    "Dr. Grace Adebayo",
    "Dr. Michael Eze",
    "Dr. Sarah Ibrahim",
]

APPOINTMENT_TIMES = ["09:00", "10:00", "11:00", "14:00"]

SAMPLE_PATIENTS = [
    ("Ada Patient", "ada.patient@example.com"),
    ("John Patient", "john.patient@example.com"),
    ("Mary Patient", "mary.patient@example.com"),
    ("David Patient", "david.patient@example.com"),
    ("Grace Patient", "grace.patient@example.com"),
    ("Peter Patient", "peter.patient@example.com"),
    ("Sarah Patient", "sarah.patient@example.com"),
    ("Daniel Patient", "daniel.patient@example.com"),
    ("Esther Patient", "esther.patient@example.com"),
    ("Michael Patient", "michael.patient@example.com"),
    ("Ruth Patient", "ruth.patient@example.com"),
    ("James Patient", "james.patient@example.com"),
    ("Joy Patient", "joy.patient@example.com"),
    ("Samuel Patient", "samuel.patient@example.com"),
    ("Faith Patient", "faith.patient@example.com"),
]


def read_api_key():
    env_file = Path(".env")

    if not env_file.exists():
        raise FileNotFoundError("Could not find .env in the project root.")

    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if line.startswith("API_KEY="):
            return line.split("=", 1)[1].strip().strip("\"'")

    raise ValueError("API_KEY was not found in .env.")


def api_request(path, method="GET", payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        method=method,
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}

    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8")
        raise RuntimeError(
            f"{method} {path} failed with HTTP {error.code}: {body}"
        ) from error


def next_weekdays(count):
    days = []
    current = datetime.now(TIMEZONE).date() + timedelta(days=1)

    while len(days) < count:
        if current.weekday() < 5:
            days.append(current)

        current += timedelta(days=1)

    return days


def create_slots():
    slots = []
    dates = next_weekdays(5)
    slot_number = 1

    for appointment_date in dates:
        for provider in PROVIDERS:
            for appointment_time in APPOINTMENT_TIMES:
                start = datetime.combine(
                    appointment_date,
                    datetime.strptime(appointment_time, "%H:%M").time(),
                    tzinfo=TIMEZONE,
                )

                end = start + timedelta(minutes=30)

                slots.append({
                    "id": f"demo-{slot_number:03d}",
                    "provider": provider,
                    "start_time": start.isoformat(),
                    "end_time": end.isoformat(),
                })

                slot_number += 1

    return slots


def create_sample_bookings(slots):
    successful = 0

    for slot, (name, email) in zip(slots, SAMPLE_PATIENTS):
        result = api_request(
            "/bookings",
            method="POST",
            payload={
                "slot_id": slot["id"],
                "name": name,
                "email": email,
            },
        )

        successful += 1
        print(f"Booked {slot['id']} for {name}")

    return successful


if __name__ == "__main__":
    API_KEY = read_api_key()

    slots = create_slots()

    print(f"Generated {len(slots)} appointment slots.")
    print("Resetting the Render database...")

    reset_result = api_request(
        "/reset",
        method="POST",
        payload={"slots": slots},
    )

    print("Database reset completed.")
    print(reset_result)

    print("\nCreating sample bookings...")

    booking_count = create_sample_bookings(slots)

    print("\nSeeding completed successfully.")
    print(f"Appointment slots created: {len(slots)}")
    print(f"Sample bookings created: {booking_count}")
    print(f"Available slots remaining: {len(slots) - booking_count}")

# Clinic Booking API

A containerized clinic appointment booking application built with **FastAPI, PostgreSQL, SQLAlchemy, and Docker**. It provides a REST API for viewing appointment availability, creating bookings, retrieving booking records, and cancelling appointments.

The project focuses on reliable booking operations, including concurrency control, idempotent requests, cursor-based pagination, and database-backed rate limiting.

**Live Application:** https://clinic-booking-app-hrsx.onrender.com/

**API Documentation:** https://clinic-booking-app-hrsx.onrender.com/docs

---

## Features

- **Appointment availability:** Retrieve available appointment slots and filter by healthcare provider.
- **Appointment booking:** Create bookings with validated patient information.
- **Concurrency control:** Prevent multiple patients from booking the same slot through database row locking and a partial unique index.
- **Idempotency:** Support idempotency keys to prevent duplicate bookings when clients retry requests.
- **Booking retrieval:** Retrieve individual bookings and list bookings associated with an email address.
- **Cursor-based pagination:** Retrieve booking history in consistent, ordered pages.
- **Appointment cancellation:** Cancel bookings without deleting their records.
- **Rate limiting:** Limit booking attempts to five per email address within a 60-second window.
- **API key authentication:** Protect application API routes using an API key.
- **Timezone-aware scheduling:** Store timezone-aware appointment timestamps and return ISO 8601 timestamps.
- **Frontend interface:** Provide a browser-based appointment booking experience.
- **Database migrations:** Manage database schema changes using Alembic.
- **Containerization:** Use Docker for the application and PostgreSQL development environment.

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| Database | PostgreSQL 17 |
| ORM | SQLAlchemy 2 |
| Data validation | Pydantic |
| Migrations | Alembic |
| Dependency management | uv |
| Frontend | HTML, CSS, JavaScript |
| Containerization | Docker |
| Testing | pytest, pytest-cov |
| Code quality | Ruff |
| Deployment | Render |

## Architecture

The application follows a simple client-server architecture.

```text
          Patient / API Client
                   |
                   v
          Frontend (HTML/CSS/JS)
                   |
                   v
             FastAPI Backend
                   |
          +--------+---------+
          |        |         |
          v        v         v
       Routes   Security  Validation
          |
          v
       SQLAlchemy
          |
          v
       PostgreSQL
```

The frontend communicates with the backend through HTTP requests. The backend validates requests, enforces authentication and booking rules, and interacts with PostgreSQL through SQLAlchemy.

Alembic manages database migrations.

## API Endpoints

All routes below are relative to the application base URL.

### Authentication

Authenticated API routes require the following header:

```http
X-API-Key: YOUR_API_KEY
```

The `/health` endpoint is currently public.

### Appointment Slots

| Method | Endpoint | Description |
|---|---|---|
| GET | `/slots` | Retrieve appointment slots |
| POST | `/reset` | Replace all appointment slots |

Filter slots by provider:

```http
GET /slots?provider=Dr.%20Ada%20Okafor
```

Example response:

```json
{
  "slots": [
    {
      "id": "demo-001",
      "provider": "Dr. Ada Okafor",
      "start_time": "2026-11-13T08:00:00Z",
      "end_time": "2026-11-13T08:30:00Z",
      "available": true
    }
  ]
}
```

The `/reset` endpoint replaces the existing slots. Because bookings are associated with slots through a cascading foreign key, resetting slots also deletes their associated bookings. This endpoint should only be used for controlled initialization or administrative purposes.

### Bookings

| Method | Endpoint | Description |
|---|---|---|
| POST | `/bookings` | Create a booking |
| GET | `/bookings/{booking_id}` | Retrieve an individual booking |
| GET | `/bookings` | List bookings by email |
| DELETE | `/bookings/{booking_id}` | Cancel a booking |

Create a booking:

```http
POST /bookings
Content-Type: application/json
X-API-Key: YOUR_API_KEY
Idempotency-Key: unique-request-key
```

Request body:

```json
{
  "slot_id": "demo-001",
  "name": "John Doe",
  "email": "john@example.com"
}
```

A successful request returns HTTP `201 Created`.

Example response:

```json
{
  "id": "generated-booking-id",
  "slot_id": "demo-001",
  "name": "John Doe",
  "email": "john@example.com",
  "status": "confirmed",
  "created_at": "2026-11-12T10:00:00Z"
}
```

The `Idempotency-Key` header is optional. When supplied, the application associates the key with a hash of the original request. Reusing the key with the same request returns the existing booking, while reusing it with a different request returns HTTP `422`.

### Booking Pagination

Bookings can be retrieved using an email address and optional pagination parameters.

```http
GET /bookings?email=john@example.com&limit=10
```

To retrieve the next page:

```http
GET /bookings?email=john@example.com&limit=10&cursor=NEXT_CURSOR
```

The response contains:

```json
{
  "bookings": [],
  "next_cursor": "NEXT_CURSOR"
}
```

The default page size is 10, with a maximum of 50 records per request. A `null` cursor indicates that there are no additional pages.

### Cancellation

```http
DELETE /bookings/{booking_id}
```

Cancellation changes the booking status to `cancelled` rather than deleting the record. Cancelled bookings no longer make their appointment slots unavailable.

### Health Check

```http
GET /health
```

Returns the application and database connection status.

## Engineering Decisions

### 1. Concurrency Control

Two simultaneous requests must not be able to confirm bookings for the same appointment slot.

The booking operation uses PostgreSQL row-level locking through SQLAlchemy's `SELECT ... FOR UPDATE`.

A partial unique index provides an additional database-level constraint allowing only one confirmed booking per slot.

This combines application-level synchronization with database-enforced consistency.

### 2. Idempotency

Network failures can cause clients to retry requests even when the original request succeeded.

The application supports an optional `Idempotency-Key` header. It stores the key alongside a SHA-256 fingerprint of the request.

This allows repeated requests with the same key and payload to return the original booking instead of creating another one.

### 3. Cursor-Based Pagination

Booking history uses cursor-based pagination rather than offset pagination.

The cursor encodes the creation timestamp and booking ID of the last returned record. Subsequent requests use these values to retrieve records after that position.

Ordering by both fields provides a deterministic ordering when multiple bookings share a timestamp.

### 4. Rate Limiting

The application permits a maximum of five booking attempts per normalized email address within a rolling 60-second window.

PostgreSQL advisory transaction locks serialize rate-limit checks for the same email address.

Attempt records are stored in the `booking_attempts` table, and expired records are removed during subsequent checks.

Requests exceeding the limit receive HTTP `429 Too Many Requests` and a `Retry-After` header.

### 5. Timezone-Aware Scheduling

Appointment timestamps are timezone-aware.

Appointments are generated using the `Africa/Lagos` timezone, stored in PostgreSQL using `TIMESTAMP WITH TIME ZONE`, and serialized as ISO 8601 timestamps.

The frontend uses the browser's local timezone when displaying appointments.

### 6. Database Integrity

The database schema includes constraints and indexes for:

- Valid appointment start and end times.
- Valid booking statuses.
- One confirmed booking per appointment slot.
- Unique non-null idempotency keys.
- Efficient booking retrieval and pagination.

## Database Models

The application uses three primary database models.

| Model | Purpose |
|---|---|
| `Slot` | Stores appointment slots and healthcare provider information |
| `Booking` | Stores patient booking information and booking status |
| `BookingAttempt` | Tracks booking attempts for rate limiting |

Database schema changes are managed through Alembic migrations.

## Local Development

### Prerequisites

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Git

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd clinic-api
```

### 2. Install dependencies

```bash
uv sync --group dev
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql+psycopg://clinic_user:YOUR_LOCAL_PASSWORD@localhost:5432/clinic_booking
API_KEY=YOUR_SECRET_API_KEY
```

Do not commit this file to version control.

### 4. Start PostgreSQL

The provided Docker Compose configuration starts the PostgreSQL database:

```bash
docker compose up -d db
```

Check its status:

```bash
docker compose ps
```

### 5. Run database migrations

```bash
uv run alembic upgrade head
```

### 6. Start the application

```bash
uv run uvicorn app.main:app --reload
```

The application will be available at:

```text
http://localhost:8000
```

API documentation:

```text
http://localhost:8000/docs
```

## Docker

Build the application image:

```bash
docker build -t clinic-api:latest .
```

Run the container with the required environment variables:

```bash
docker run -p 8000:8000 --env-file .env clinic-api:latest
```

The application container runs database migrations before starting the FastAPI server.

The supplied `compose.yaml` currently defines the PostgreSQL development service.

## Testing

The project uses pytest for automated testing.

Run the complete test suite:

```bash
uv run pytest
```

Run tests with coverage:

```bash
uv run pytest --cov=app --cov-report=term-missing
```

The test suite covers:

- Slot retrieval and filtering
- Booking creation and validation
- API key authentication
- Concurrent booking attempts
- Idempotency
- Cursor-based pagination
- Rate limiting
- Database models

## Deployment

The application is deployed on Render using Docker.

The deployment process includes:

1. Building the application Docker image.
2. Connecting to the managed PostgreSQL database.
3. Applying Alembic migrations.
4. Starting the Uvicorn server.

The application requires the following environment variables in its deployment environment:

- `DATABASE_URL`
- `API_KEY`

Secrets should be configured through the hosting provider's environment-variable settings rather than committed to source control.

## Database Seeding Scripts

The project includes two utility scripts used to populate the deployed Render PostgreSQL database with demonstration data.

- **`seed_render.py`** — Creates the initial demonstration dataset by populating the database with sample providers, appointment slots, and bookings. It also includes a database reset operation before inserting the data. **Use with caution:** running this script against an existing database can delete existing bookings and slots.

- **`add_pagination_bookings.py`** — Adds additional sample bookings associated with a demonstration email address. These records were created to test and demonstrate the cursor-based pagination functionality of the `GET /bookings` endpoint.

These scripts are intended for database setup and testing, not automatic application startup. They should only be executed intentionally, with the correct database connection configured. Avoid running the reset operation against a database containing real user data.

## Project Structure

```text
clinic-api/
│
├── app/
│   ├── config.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   ├── rate_limit.py
│   ├── routes.py
│   ├── schemas.py
│   └── security.py
│
├── frontend/
│   ├── app.js
│   ├── index.html
│   └── style.css
│
├── migrations/
│
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_bookings.py
│   ├── test_concurrency.py
│   ├── test_idempotency.py
│   ├── test_models.py
│   ├── test_pagination.py
│   ├── test_rate_limit.py
│   ├── test_slots.py
│   └── test_validation.py
│
├── .dockerignore
├── .gitignore
├── alembic.ini
├── compose.yaml
├── Dockerfile
├── pyproject.toml
├── uv.lock
└── README.md
```

---

## License

MIT License
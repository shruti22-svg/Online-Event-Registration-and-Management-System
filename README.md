# Online Event Registration and Management System

College event registration app with separate pages for student registration, login, event listing, event registration, participants, confirmation, and admin dashboard.

## Modules

- Student registration and login
- Event listing
- Event registration
- View registered participants
- Admin dashboard
- Registration confirmation

## Demo accounts

- Student: `student@college.edu` / `student123`
- Admin: `admin@college.edu` / `admin123`

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

Open http://localhost:5002

## Run with Docker

```bash
docker compose up --build -d
```

Open http://localhost:5002

## Selenium tests

```bash
docker compose -f docker-compose.ci.yml up --build --abort-on-container-exit --exit-code-from tests
```

| Test ID | Test case | Expected result |
| --- | --- | --- |
| TC01 | Open registration page | Page should load |
| TC02 | Register with valid details | Registration successful |
| TC03 | Submit empty form | Validation message |
| TC04 | Enter invalid email | Error message |
| TC05 | Register with duplicate email | Duplicate registration prevented |
| TC06 | Login with valid credentials | Dashboard displayed |
| TC07 | View registered events | Correct events displayed |

## Jenkins

Jenkins is available at http://localhost:8081 (`admin` / `admin123`). Job: `event-registration-system`.

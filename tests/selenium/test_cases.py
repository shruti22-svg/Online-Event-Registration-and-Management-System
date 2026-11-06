import os
import sys
import time
import uuid

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE_URL = os.environ.get("BASE_URL", "http://localhost:5002").rstrip("/")
SELENIUM_REMOTE_URL = os.environ.get("SELENIUM_REMOTE_URL")


def wait_for_app():
    deadline = time.time() + 60
    last_error = None
    while time.time() < deadline:
        try:
            response = requests.get(f"{BASE_URL}/api/health", timeout=3)
            if response.ok:
                return
            last_error = response.status_code
        except Exception as error:
            last_error = error
        time.sleep(1)
    raise RuntimeError(f"App did not become ready: {last_error}")


def build_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    if SELENIUM_REMOTE_URL:
        return webdriver.Remote(command_executor=SELENIUM_REMOTE_URL, options=options)
    return webdriver.Chrome(options=options)


def fill(driver, element_id, value):
    field = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, element_id)))
    field.clear()
    field.send_keys(value)


def click(driver, element_id):
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, element_id))).click()


def text_of(driver, element_id):
    return WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, element_id))).text


def run():
    wait_for_app()
    driver = build_driver()
    results = []
    stamp = uuid.uuid4().hex[:8]
    email = f"sel.student.{stamp}@college.edu"
    password = "Pass1234"

    def record(case_id, name, expected, ok, actual=""):
        results.append((case_id, name, expected, "PASS" if ok else "FAIL", actual))
        if not ok:
            raise AssertionError(f"{case_id} failed: {actual}")

    try:
        driver.get(f"{BASE_URL}/register")
        title = text_of(driver, "page-title")
        record("TC01", "Open registration page", "Page should load", "Student Registration" in title, title)

        click(driver, "register-btn")
        empty_msg = text_of(driver, "register-message")
        record(
            "TC03",
            "Submit empty form",
            "Validation message",
            "fill all fields" in empty_msg.lower(),
            empty_msg,
        )

        fill(driver, "name", "Selenium Student")
        fill(driver, "email", "not-an-email")
        fill(driver, "password", password)
        fill(driver, "student_id", "STU9001")
        fill(driver, "phone", "9998887776")
        click(driver, "register-btn")
        invalid_msg = text_of(driver, "register-message")
        record(
            "TC04",
            "Enter invalid email",
            "Error message",
            "valid email" in invalid_msg.lower(),
            invalid_msg,
        )

        fill(driver, "name", "Selenium Student")
        fill(driver, "email", email)
        fill(driver, "password", password)
        fill(driver, "student_id", "STU9001")
        fill(driver, "phone", "9998887776")
        click(driver, "register-btn")
        WebDriverWait(driver, 10).until(EC.url_contains("/login"))
        banner = text_of(driver, "banner")
        record(
            "TC02",
            "Register with valid details",
            "Registration successful",
            "registration successful" in banner.lower(),
            banner,
        )

        driver.get(f"{BASE_URL}/register")
        fill(driver, "name", "Duplicate User")
        fill(driver, "email", email)
        fill(driver, "password", password)
        fill(driver, "student_id", "STU9002")
        fill(driver, "phone", "9998887777")
        click(driver, "register-btn")
        dup_msg = text_of(driver, "register-message")
        record(
            "TC05",
            "Register with duplicate email",
            "Duplicate registration prevented",
            "duplicate" in dup_msg.lower(),
            dup_msg,
        )

        driver.get(f"{BASE_URL}/login")
        fill(driver, "login-email", email)
        fill(driver, "login-password", password)
        click(driver, "login-btn")
        WebDriverWait(driver, 10).until(EC.url_contains("/dashboard"))
        dash = text_of(driver, "dashboard-title")
        record("TC06", "Login with valid credentials", "Dashboard displayed", "Dashboard" in dash, dash)

        driver.get(f"{BASE_URL}/events")
        events_title = text_of(driver, "events-title")
        first_register = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".register-link"))
        )
        event_name = driver.find_element(By.CSS_SELECTOR, ".event-title").text
        first_register.click()
        click(driver, "event-register-btn")
        WebDriverWait(driver, 10).until(EC.url_contains("/confirmation/"))
        confirmed = text_of(driver, "confirmed-event")
        driver.get(f"{BASE_URL}/my-events")
        table_text = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "registered-events-table"))
        ).text
        listing_ok = "Event Listing" in events_title and event_name in confirmed and event_name in table_text
        record(
            "TC07",
            "View registered events",
            "Correct events displayed",
            listing_ok,
            f"listed={events_title}; confirmed={confirmed}; my_events={table_text}",
        )
    finally:
        driver.quit()

    print("Test ID | Test case | Expected result | Status")
    print("-" * 72)
    for row in results:
        print(f"{row[0]} | {row[1]} | {row[2]} | {row[3]}")
    print("All Selenium test cases passed.")


if __name__ == "__main__":
    try:
        run()
    except Exception as error:
        print(f"TEST RUN FAILED: {error}")
        sys.exit(1)

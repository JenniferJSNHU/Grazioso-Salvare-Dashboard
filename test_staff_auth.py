import base64
import os
import unittest
from unittest.mock import patch

from flask import Flask
from werkzeug.security import generate_password_hash
from staff_auth import enable_staff_auth


class TestStaffAuthentication(unittest.TestCase):

    def setUp(self):
        # configure temporary test credentials
        self.password = "test-password-123"
        credentials = {
            "GRAZIOSO_STAFF_USER": "staff",
            "GRAZIOSO_STAFF_PASSWORD_HASH": generate_password_hash(self.password),
        }

        self.environment = patch.dict(os.environ, credentials)
        self.environment.start()
        self.addCleanup(self.environment.stop)

        # create an isolated flask application
        self.app = Flask(__name__)
        self.app.add_url_rule("/", "index", lambda: "Dashboard")
        enable_staff_auth(self.app)
        self.client = self.app.test_client()

    # create a basic authentication header
    def auth_header(self, username, password):
        encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
        return {"Authorization": f"Basic {encoded}"}

    # allow access with valid credentials
    def test_valid_credentials(self):
        response = self.client.get(
            "/", headers=self.auth_header("staff", self.password)
        )
        self.assertEqual(response.status_code, 200)

    # reject incorrect passwords
    def test_invalid_password(self):
        response = self.client.get(
            "/", headers=self.auth_header("staff", "wrong-password")
        )
        self.assertEqual(response.status_code, 401)

    # reject requests without authentication
    def test_missing_credentials(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 401)

    # reject requests when authentication is not configured
    def test_missing_configuration(self):
        with patch.dict(
            os.environ,
            {
                "GRAZIOSO_STAFF_USER": "",
                "GRAZIOSO_STAFF_PASSWORD_HASH": "",
            },
        ):
            response = self.client.get("/")
            self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()

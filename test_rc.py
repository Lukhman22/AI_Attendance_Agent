import requests
import json
import os
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000/api"

print("Starting Release Candidate API Verification...")

# We'll just verify the endpoints are available and return expected structures
# Wait, the backend isn't running. Let's start it in the background if it's not running!

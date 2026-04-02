from firebase_functions import https_fn
from firebase_admin import initialize_app
import google.generativeai as genai

# Initialize Firebase Admin
initialize_app()

@https_fn.on_request()
def generate_proposal(req: https_fn.Request) -> https_fn.Response:
    """
    This is the main entry point for your ProPAS AI logic.
    For now, it's a simple health check to see if your deploy worked.
    """
    return https_fn.Response("ProPAS AI Backend is officially LIVE!")
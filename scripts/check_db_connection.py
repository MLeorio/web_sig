"""Vérifie rapidement que la base de données définie dans .env est joignable.

Usage :
    venv\\Scripts\\python.exe scripts\\check_db_connection.py
"""
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

load_dotenv()

url = os.getenv("DATABASE_URL")

try:
    engine = create_engine(url)

    with engine.connect() as conn:
        print("Connexion réussie !")
except Exception as e:
    print("Erreur :", e)

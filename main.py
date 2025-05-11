import os
import requests
import logging
from datetime import datetime

# --- Configurar logging ---
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Variables de entorno ---
RADARR_URL = os.getenv('RADARR_URL')
RADARR_API_KEY = os.getenv('RADARR_API_KEY')
YEAR_THRESHOLD = int(os.getenv('YEAR_THRESHOLD', 2024))

HEADERS = {
    'X-Api-Key': RADARR_API_KEY,
    'Content-Type': 'application/json'
}

def get_movies():
    response = requests.get(f"{RADARR_URL}/api/v3/movie", headers=HEADERS)
    response.raise_for_status()
    return response.json()

def add_to_exclusion(tmdb_id, title):
    logging.info(f"Añadiendo '{title}' a la lista de exclusión")
    payload = {"tmdbId": tmdb_id}
    response = requests.post(f"{RADARR_URL}/api/v3/importlistexclusion", json=payload, headers=HEADERS)
    if response.status_code != 201:
        logging.warning(f"Error al excluir '{title}': {response.text}")

def delete_movie(movie_id, title):
    logging.info(f"Eliminando película y archivos: '{title}' (ID: {movie_id})")
    response = requests.delete(
        f"{RADARR_URL}/api/v3/movie/{movie_id}?deleteFiles=true&addImportListExclusion=false",
        headers=HEADERS
    )
    if response.status_code != 200:
        logging.warning(f"Error al eliminar '{title}': {response.text}")

def run():
    logging.info("⏳ Iniciando revisión de películas...")
    try:
        movies = get_movies()
        removed = 0
        for movie in movies:
            year = movie.get("year", 9999)
            if year < YEAR_THRESHOLD:
                title = movie.get("title", "Desconocida")
                tmdb_id = movie.get("tmdbId")
                movie_id = movie.get("id")

                delete_movie(movie_id, title)
                add_to_exclusion(tmdb_id, title)
                removed += 1

        logging.info(f"✅ Revisión completada. {removed} películas eliminadas.")
    except Exception as e:
        logging.error(f"❌ Error general: {e}")

if __name__ == "__main__":
    run()

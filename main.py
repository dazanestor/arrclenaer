import os
import requests
import logging
import re
from requests.auth import HTTPBasicAuth

# --- Configuración de logging ---
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Variables de entorno ---
RADARR_URL = os.getenv('RADARR_URL')
RADARR_API_KEY = os.getenv('RADARR_API_KEY')
YEAR_THRESHOLD = int(os.getenv('YEAR_THRESHOLD', 2024))
TRANSMISSION_URL = os.getenv('TRANSMISSION_URL', 'http://localhost:9091')
TRANSMISSION_USER = os.getenv('TRANSMISSION_USER', 'usuario')
TRANSMISSION_PASSWORD = os.getenv('TRANSMISSION_PASSWORD', 'contraseña')

HEADERS = {
    'X-Api-Key': RADARR_API_KEY,
    'Content-Type': 'application/json'
}

def get_movies():
    response = requests.get(f"{RADARR_URL}/api/v3/movie", headers=HEADERS)
    response.raise_for_status()
    return response.json()

def add_to_exclusion(tmdb_id, title, year):
    if not tmdb_id or not year:
        logging.warning(f"No se puede excluir '{title}' porque falta tmdbId o año.")
        return

    payload = {
        "tmdbId": tmdb_id,
        "movieTitle": title,
        "movieYear": year
    }

    logging.info(f"Añadiendo '{title}' a la lista de exclusión")
    response = requests.post(f"{RADARR_URL}/api/v3/exclusions", json=payload, headers=HEADERS)

    if response.status_code not in (200, 201):
        logging.warning(f"Error al excluir '{title}': {response.text}")

def get_transmission_session_id():
    response = requests.post(
        f"{TRANSMISSION_URL}/transmission/rpc",
        auth=HTTPBasicAuth(TRANSMISSION_USER, TRANSMISSION_PASSWORD)
    )
    return response.headers.get("X-Transmission-Session-Id")

def cancel_torrent_download(title):
    logging.info(f"Comprobando si '{title}' está en descarga en Transmission...")
    session_id = get_transmission_session_id()
    if not session_id:
        logging.warning("No se pudo obtener el Session ID de Transmission.")
        return

    headers = {"X-Transmission-Session-Id": session_id}
    response = requests.post(
        f"{TRANSMISSION_URL}/transmission/rpc",
        json={
            "method": "torrent-get",
            "arguments": {"fields": ["id", "name"]}
        },
        auth=HTTPBasicAuth(TRANSMISSION_USER, TRANSMISSION_PASSWORD),
        headers=headers
    )

    if response.status_code == 409:
        logging.warning("Session ID de Transmission inválido.")
        return
    elif response.status_code != 200:
        logging.warning("No se pudo obtener la lista de torrents de Transmission.")
        return

    torrents = response.json().get('arguments', {}).get('torrents', [])
    title_lower = title.lower()

    for torrent in torrents:
        if re.search(r'\b' + re.escape(title_lower) + r'\b', torrent['name'].lower()):
            logging.info(f"Eliminando torrent de '{title}' de Transmission (ID: {torrent['id']})")
            response = requests.post(
                f"{TRANSMISSION_URL}/transmission/rpc",
                json={
                    "method": "torrent-remove",
                    "arguments": {
                        "ids": [torrent['id']],
                        "delete-local-data": True
                    }
                },
                auth=HTTPBasicAuth(TRANSMISSION_USER, TRANSMISSION_PASSWORD),
                headers=headers
            )
            if response.status_code == 200:
                logging.info(f"Torrent de '{title}' eliminado correctamente de Transmission")
            else:
                logging.warning(f"No se pudo eliminar el torrent de '{title}'")
            break

def delete_movie(movie_id, title):
    logging.info(f"Eliminando película y archivos: '{title}' (ID: {movie_id})")
    response = requests.delete(
        f"{RADARR_URL}/api/v3/movie/{movie_id}?deleteFiles=true&addImportListExclusion=false",
        headers=HEADERS
    )
    if response.status_code != 200:
        logging.warning(f"Error al eliminar '{title}': {response.text}")
    else:
        cancel_torrent_download(title)

def run():
    logging.info("⏳ Iniciando revisión de películas...")
    try:
        movies = get_movies()
        removed = 0
        for movie in movies:
            year = movie.get("year")
            if year and year < YEAR_THRESHOLD:
                title = movie.get("title", "Desconocida")
                tmdb_id = movie.get("tmdbId")
                movie_id = movie.get("id")

                delete_movie(movie_id, title)
                add_to_exclusion(tmdb_id, title, year)
                removed += 1

        logging.info(f"✅ Revisión completada. {removed} películas eliminadas.")
    except Exception as e:
        logging.error(f"❌ Error general: {e}")

if __name__ == "__main__":
    run()

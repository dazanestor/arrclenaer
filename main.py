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
TRANSMISSION_USER = os.getenv('TRANSMISSION_USER', 'usuario')  # Usuario de Transmission
TRANSMISSION_PASSWORD = os.getenv('TRANSMISSION_PASSWORD', 'contraseña')  # Contraseña de Transmission

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
    else:
        cancel_torrent_download(title)

def cancel_torrent_download(title):
    logging.info(f"Comprobando si '{title}' está en descarga en Transmission...")
    
    # Obtener todos los torrents activos
    params = {'fields': 'id,name'}
    response = requests.post(f"{TRANSMISSION_URL}/transmission/rpc", json={
        "method": "torrent-get",
        "arguments": params
    }, auth=HTTPBasicAuth(TRANSMISSION_USER, TRANSMISSION_PASSWORD))
    
    if response.status_code == 200:
        torrents = response.json().get('arguments', {}).get('torrents', [])
        
        # Convertir el nombre de la película a minúsculas para hacer la comparación insensible al caso
        title_lower = title.lower()
        
        for torrent in torrents:
            # Buscar el nombre de la película en el nombre completo del torrent de manera flexible
            if re.search(r'\b' + re.escape(title_lower) + r'\b', torrent['name'].lower()):
                logging.info(f"Eliminando torrent de '{title}' de Transmission (ID: {torrent['id']})")
                # Eliminar el torrent de Transmission
                response = requests.post(f"{TRANSMISSION_URL}/transmission/rpc", json={
                    "method": "torrent-remove",
                    "arguments": {
                        "ids": [torrent['id']],
                        "delete-local-data": True
                    }
                }, auth=HTTPBasicAuth(TRANSMISSION_USER, TRANSMISSION_PASSWORD))
                
                if response.status_code == 200:
                    logging.info(f"Torrent de '{title}' eliminado correctamente de Transmission")
                else:
                    logging.warning(f"No se pudo eliminar el torrent de '{title}' en Transmission")
                break
    else:
        logging.warning("No se pudo obtener la lista de torrents de Transmission")

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

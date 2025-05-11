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

# Función para obtener el X-Transmission-Session-Id
def get_session_id():
    response = requests.post(f"{TRANSMISSION_URL}/transmission/rpc", json={
        "method": "torrent-get",
        "arguments": {"fields": ["id", "name"]}
    }, auth=HTTPBasicAuth(TRANSMISSION_USER, TRANSMISSION_PASSWORD))
    
    if response.status_code == 409:
        # Extraemos el nuevo Session-Id de la cabecera
        session_id = response.headers['X-Transmission-Session-Id']
        return session_id
    return None

# Función para obtener la lista de torrents
def get_torrents(session_id):
    response = requests.post(f"{TRANSMISSION_URL}/transmission/rpc", json={
        "method": "torrent-get",
        "arguments": {"fields": ["id", "name"]}
    }, headers={"X-Transmission-Session-Id": session_id}, auth=HTTPBasicAuth(TRANSMISSION_USER, TRANSMISSION_PASSWORD))
    
    if response.status_code == 200:
        return response.json().get('arguments', {}).get('torrents', [])
    return []

# Función para normalizar el nombre de los torrents y las películas
def normalize_title(title):
    # Convertir a minúsculas, eliminar caracteres no alfanuméricos, y eliminar información adicional
    title = re.sub(r'[^a-zA-Z0-9\s]', '', title.lower())  # Eliminar caracteres especiales
    title = re.sub(r'\s+', ' ', title)  # Normalizar espacios
    return title.strip()

# Función para eliminar un torrent
def remove_torrent(torrent_id, session_id):
    response = requests.post(f"{TRANSMISSION_URL}/transmission/rpc", json={
        "method": "torrent-remove",
        "arguments": {
            "ids": [torrent_id],
            "delete-local-data": True
        }
    }, headers={"X-Transmission-Session-Id": session_id}, auth=HTTPBasicAuth(TRANSMISSION_USER, TRANSMISSION_PASSWORD))
    
    if response.status_code == 200:
        logging.info(f"Torrent con ID {torrent_id} eliminado correctamente de Transmission.")
    else:
        logging.warning(f"No se pudo eliminar el torrent con ID {torrent_id}.")

# Función para obtener las películas de Radarr
def get_movies():
    response = requests.get(f"{RADARR_URL}/api/v3/movie", headers=HEADERS)
    response.raise_for_status()
    return response.json()

# Función para agregar una película a la lista de exclusión en Radarr
def add_to_exclusion(tmdb_id, title, movie_year):
    logging.info(f"Añadiendo '{title}' (Año: {movie_year}) a la lista de exclusión")
    payload = {
        "tmdbId": tmdb_id,
        "movieYear": movie_year
    }
    response = requests.post(f"{RADARR_URL}/api/v3/importlistexclusion", json=payload, headers=HEADERS)
    if response.status_code != 201:
        logging.warning(f"Error al excluir '{title}': {response.text}")
    else:
        logging.info(f"'{title}' excluida correctamente.")

# Función para eliminar una película en Radarr
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

# Función para cancelar la descarga de torrents en Transmission
def cancel_torrent_download(title):
    logging.info(f"Comprobando si '{title}' está en descarga en Transmission...")
    
    # Obtener la sesión de Transmission (session_id)
    session_id = get_session_id()
    if session_id is None:
        logging.warning("No se pudo obtener el Session ID de Transmission.")
        return

    # Obtener todos los torrents activos
    torrents = get_torrents(session_id)
    
    if torrents:
        # Normalizar el nombre de la película
        normalized_title = normalize_title(title)

        for torrent in torrents:
            # Normalizar el nombre del torrent y compararlo con el nombre de la película
            normalized_torrent_name = normalize_title(torrent['name'])

            # Realizamos la comparación entre los nombres normalizados
            if normalized_title in normalized_torrent_name:
                logging.info(f"Eliminando torrent de '{title}' de Transmission (ID: {torrent['id']})")
                # Eliminar el torrent de Transmission
                remove_torrent(torrent['id'], session_id)
                break
    else:
        logging.warning("No se encontraron torrents activos en Transmission.")

# Función principal
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

                # Solo eliminar y excluir si la película tiene tmdb_id y movie_year disponibles
                if tmdb_id and year:
                    delete_movie(movie_id, title)
                    add_to_exclusion(tmdb_id, title, year)
                    removed += 1
                else:
                    logging.warning(f"No se pudo excluir o eliminar '{title}' debido a falta de datos.")
        
        logging.info(f"✅ Revisión completada. {removed} películas eliminadas.")
    except Exception as e:
        logging.error(f"❌ Error general: {e}")

if __name__ == "__main__":
    run()

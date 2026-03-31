import logging
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from django.conf import settings

logger = logging.getLogger(__name__)


class TMDBService:
    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self):
        self.api_key = ""
        self.session = None

    def _ensure_init(self):
        if not self.session:
            self.api_key = getattr(settings, 'TMDB_API_KEY', '')
            self.session = self._create_session()

    def _create_session(self):
        """Create a requests session with automatic retry on failures."""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,  # 0.5s, 1s, 2s between retries
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20,
        )
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _get(self, endpoint, params=None):
        self._ensure_init()
        if params is None:
            params = {}
        params["api_key"] = self.api_key
        url = f"{self.BASE_URL}{endpoint}"
        try:
            r = self.session.get(url, params=params, timeout=(5, 10))
            r.raise_for_status()
            return r.json()
        except (requests.exceptions.ConnectionError, ConnectionResetError) as e:
            # Session might be stale — recreate and retry once
            logger.warning(f"TMDB connection error {endpoint}, reconnecting: {e}")
            self.session = self._create_session()
            try:
                r = self.session.get(url, params=params, timeout=(5, 10))
                r.raise_for_status()
                return r.json()
            except Exception as e2:
                logger.warning(f"TMDB reconnect failed {endpoint}: {e2}")
                return {"_error": True, "_message": "Connection failed. Please try again."}
        except requests.exceptions.Timeout:
            logger.warning(f"TMDB timeout {endpoint}")
            return {"_error": True, "_message": "Request timed out. Please try again."}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else 0
            if status == 429:
                logger.warning(f"TMDB rate limited {endpoint}")
                return {"_error": True, "_message": "Too many requests. Please wait a moment."}
            logger.warning(f"TMDB HTTP {status} {endpoint}")
            return {"_error": True, "_message": f"API error ({status}). Please try again."}
        except Exception as e:
            logger.warning(f"TMDB error {endpoint}: {e}")
            return {"_error": True, "_message": "Something went wrong. Please try again."}

    def is_error(self, data):
        """Check if a TMDB response is an error."""
        return isinstance(data, dict) and data.get("_error", False)

    def get_trending(self, page=1, region="US", window="week"):
        return self._get(f"/trending/movie/{window}", {"page": page, "region": region})

    def get_popular(self, page=1, region="US"):
        return self._get("/movie/popular", {"page": page, "region": region})

    def get_top_rated(self, page=1, region="US"):
        return self._get("/movie/top_rated", {"page": page, "region": region})

    def get_now_playing(self, page=1, region="US"):
        return self._get("/movie/now_playing", {"page": page, "region": region})

    def get_movie_details(self, movie_id):
        return self._get(f"/movie/{movie_id}", {"append_to_response": "credits,videos,watch/providers"})

    def search_movies(self, query, page=1, region="US"):
        return self._get("/search/movie", {
            "query": query,
            "page": page,
            "region": region,
            "include_adult": "false",
        })

    def get_by_genre(self, genre_id, page=1, region="US"):
        return self._get("/discover/movie", {
            "with_genres": genre_id,
            "page": page,
            "sort_by": "popularity.desc",
            "region": region,
        })

    def get_genres(self):
        return self._get("/genre/movie/list")


tmdb = TMDBService()

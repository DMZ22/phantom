import logging
import requests
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
            self.session = requests.Session()

    def _get(self, endpoint, params=None):
        self._ensure_init()
        if params is None:
            params = {}
        params["api_key"] = self.api_key
        try:
            r = self.session.get(
                f"{self.BASE_URL}{endpoint}",
                params=params,
                timeout=(2, 5),
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.warning(f"TMDB error {endpoint}: {e}")
            return {}

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
        return self._get("/search/movie", {"query": query, "page": page, "region": region})

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

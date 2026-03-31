"""
Phantom Hybrid Recommendation Engine
=====================================

Uses a **weighted hybrid** of three signals, combined into a single score:

1. **Content-Based Filtering (TF-IDF + Cosine Similarity)**
   - Builds a text profile per movie from title, overview, genres, cast keywords
   - Vectorizes using TF-IDF with unigrams + bigrams
   - Computes cosine similarity between seed centroid and candidate movies
   - Captures *what the movie is about* (plot, themes, genre)

2. **Metadata Feature Matching (Jaccard + Numeric Distance)**
   - Genre overlap via Jaccard similarity (shared genres / total genres)
   - Rating proximity (movies with similar vote_average)
   - Era matching (same decade bonus)
   - Language affinity (same original language)
   - Captures *structural similarity* independent of text

3. **Popularity-Quality Score (Bayesian Weighted Rating)**
   - Bayesian average: (v/(v+m)) * R + (m/(v+m)) * C
     where v=votes, m=min votes threshold, R=movie avg, C=global avg
   - Prevents obscure movies with 1 vote = 10.0 from ranking high
   - Balances discovery with quality

Final score = α * content_sim + β * metadata_sim + γ * quality_score
Default weights: α=0.50, β=0.35, γ=0.15

This runs **stateless** per request — no shared mutable state.
"""

import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)

# ─── Constants ───────────────────────────────────────────────────────────────

GENRE_MAP = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
    80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
    14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
    9648: "Mystery", 10749: "Romance", 878: "ScienceFiction",
    10770: "TVMovie", 53: "Thriller", 10752: "War", 37: "Western",
}

# Hybrid weights
W_CONTENT = 0.50   # TF-IDF cosine similarity
W_METADATA = 0.35  # Genre + rating + era + language
W_QUALITY = 0.15   # Bayesian quality score

# Bayesian rating: minimum vote count to be considered reliable
BAYES_M = 50
BAYES_C = 6.5  # Assumed global average


# ─── Feature Extraction ─────────────────────────────────────────────────────

def _get_genres(movie):
    """Extract genre names from a movie dict."""
    genres = movie.get("genres", [])
    if genres:
        return {(g.get("name", "") if isinstance(g, dict) else str(g)) for g in genres} - {""}
    genre_ids = movie.get("genre_ids", [])
    return {GENRE_MAP[gid] for gid in genre_ids if gid in GENRE_MAP}


def _get_year(movie):
    """Extract release year."""
    release = movie.get("release_date", "")
    if release and len(release) >= 4:
        try:
            return int(release[:4])
        except ValueError:
            pass
    return None


def _build_text(movie):
    """Build a rich text profile for TF-IDF vectorization."""
    parts = []

    title = movie.get("title", "")
    # Title gets 3x weight — it's the strongest identity signal
    parts.extend([title] * 3)

    overview = movie.get("overview", "")
    parts.append(overview)

    # Genre names 2x weight
    genre_names = _get_genres(movie)
    for name in genre_names:
        parts.extend([name] * 2)

    # Cast names (if available from detail endpoint)
    credits = movie.get("credits", {})
    cast = credits.get("cast", [])
    for person in cast[:5]:  # Top 5 cast members
        name = person.get("name", "")
        if name:
            parts.append(name)

    # Director (strong signal for style)
    crew = credits.get("crew", [])
    for person in crew:
        if person.get("job") == "Director":
            director = person.get("name", "")
            if director:
                parts.extend([director] * 2)  # 2x weight

    # Rating bucket
    vote = movie.get("vote_average", 0)
    if vote >= 8.5:
        parts.append("masterpiece critically_acclaimed exceptional")
    elif vote >= 7.5:
        parts.append("highly_rated excellent quality")
    elif vote >= 6.5:
        parts.append("good solid well_made")
    elif vote >= 5:
        parts.append("average decent")

    # Decade for era-matching
    year = _get_year(movie)
    if year:
        decade = (year // 10) * 10
        parts.append(f"decade_{decade}s era_{decade}s")
        # More granular: recent vs classic
        if year >= 2020:
            parts.append("contemporary modern")
        elif year >= 2000:
            parts.append("modern_classic")
        elif year >= 1980:
            parts.append("retro classic_era")
        else:
            parts.append("vintage golden_age")

    # Popularity tier
    pop = movie.get("popularity", 0)
    if pop > 200:
        parts.append("mega_blockbuster smash_hit widely_known")
    elif pop > 100:
        parts.append("blockbuster popular hit")
    elif pop > 50:
        parts.append("mainstream well_known")
    elif pop > 10:
        parts.append("moderate indie_hit")

    # Language / origin
    lang = movie.get("original_language", "")
    if lang:
        parts.append(f"language_{lang}")
        if lang != "en":
            parts.append("international foreign_language")

    return " ".join(parts)


# ─── Similarity Computations ────────────────────────────────────────────────

def _content_similarity(seed_movies, all_movies, id_map):
    """Compute TF-IDF cosine similarity between seed centroid and all movies."""
    corpus = [_build_text(m) for m in all_movies]

    vectorizer = TfidfVectorizer(
        stop_words='english',
        max_features=10000,
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.90,
        sublinear_tf=True,  # Apply log normalization to TF — reduces impact of very frequent terms
    )
    matrix = vectorizer.fit_transform(corpus)

    # Compute seed centroid
    seed_indices = [id_map[m.get("id")] for m in seed_movies if m.get("id") in id_map]
    if not seed_indices:
        return np.zeros(len(all_movies))

    seed_vectors = matrix[seed_indices]
    centroid = np.asarray(seed_vectors.mean(axis=0))

    sims = cosine_similarity(centroid, matrix).flatten()

    # Zero out seeds
    for idx in seed_indices:
        sims[idx] = -1

    return sims


def _metadata_similarity(seed_movies, all_movies):
    """Compute metadata-based similarity using genre overlap, rating, era, language."""
    # Aggregate seed features
    seed_genres = set()
    seed_ratings = []
    seed_years = []
    seed_langs = set()

    for m in seed_movies:
        seed_genres |= _get_genres(m)
        vote = m.get("vote_average", 0)
        if vote > 0:
            seed_ratings.append(vote)
        year = _get_year(m)
        if year:
            seed_years.append(year)
        lang = m.get("original_language", "")
        if lang:
            seed_langs.add(lang)

    avg_seed_rating = np.mean(seed_ratings) if seed_ratings else 6.5
    avg_seed_year = np.mean(seed_years) if seed_years else 2020

    scores = np.zeros(len(all_movies))

    for i, movie in enumerate(all_movies):
        movie_genres = _get_genres(movie)
        movie_rating = movie.get("vote_average", 0)
        movie_year = _get_year(movie)
        movie_lang = movie.get("original_language", "")

        # Genre Jaccard similarity (0 to 1)
        if seed_genres or movie_genres:
            union = seed_genres | movie_genres
            intersection = seed_genres & movie_genres
            genre_sim = len(intersection) / len(union) if union else 0
        else:
            genre_sim = 0

        # Rating proximity (0 to 1, closer = higher)
        rating_diff = abs(movie_rating - avg_seed_rating)
        rating_sim = max(0, 1 - rating_diff / 5)  # 5-point diff = 0 similarity

        # Era similarity (0 to 1)
        if movie_year:
            year_diff = abs(movie_year - avg_seed_year)
            era_sim = max(0, 1 - year_diff / 30)  # 30-year diff = 0 similarity
        else:
            era_sim = 0.3  # neutral

        # Language match (binary bonus)
        lang_sim = 1.0 if movie_lang in seed_langs else 0.3

        # Weighted combination of metadata signals
        # Genre is the strongest metadata signal
        scores[i] = (
            0.50 * genre_sim +
            0.20 * rating_sim +
            0.15 * era_sim +
            0.15 * lang_sim
        )

    return scores


def _quality_scores(all_movies):
    """Compute Bayesian weighted rating for each movie."""
    scores = np.zeros(len(all_movies))

    for i, movie in enumerate(all_movies):
        v = movie.get("vote_count", 0)
        R = movie.get("vote_average", 0)

        # Bayesian average: (v/(v+m)) * R + (m/(v+m)) * C
        if v > 0:
            scores[i] = (v / (v + BAYES_M)) * R + (BAYES_M / (v + BAYES_M)) * BAYES_C
        else:
            scores[i] = BAYES_C * 0.5  # Unknown quality penalized

    # Normalize to 0-1
    max_score = scores.max()
    if max_score > 0:
        scores = scores / max_score

    return scores


# ─── Public API ──────────────────────────────────────────────────────────────

def recommend_from_pool(seed_movies, pool, n=12,
                        w_content=W_CONTENT, w_metadata=W_METADATA, w_quality=W_QUALITY):
    """
    Hybrid recommendation: TF-IDF content + metadata matching + quality scoring.

    Args:
        seed_movies: List of movie dicts to base recommendations on
        pool: List of candidate movie dicts to recommend from
        n: Number of recommendations to return
        w_content: Weight for TF-IDF content similarity (default 0.50)
        w_metadata: Weight for metadata similarity (default 0.35)
        w_quality: Weight for quality score (default 0.15)

    Returns:
        List of recommended movie dicts, sorted by hybrid score
    """
    if not seed_movies or not pool:
        return []

    all_movies = list(seed_movies) + list(pool)
    seed_ids = {m.get("id") for m in seed_movies}
    id_map = {m.get("id"): i for i, m in enumerate(all_movies)}

    try:
        # Signal 1: Content-based (TF-IDF cosine similarity)
        content_sims = _content_similarity(seed_movies, all_movies, id_map)

        # Signal 2: Metadata matching (genre, rating, era, language)
        metadata_sims = _metadata_similarity(seed_movies, all_movies)

        # Signal 3: Quality score (Bayesian weighted rating)
        quality_scores = _quality_scores(all_movies)

        # Normalize content similarities to 0-1 range
        content_max = content_sims.max()
        if content_max > 0:
            content_norm = np.clip(content_sims / content_max, 0, 1)
        else:
            content_norm = np.zeros_like(content_sims)

        # Combine signals with weights
        hybrid_scores = (
            w_content * content_norm +
            w_metadata * metadata_sims +
            w_quality * quality_scores
        )

        # Zero out seed movies
        for m in seed_movies:
            mid = m.get("id")
            if mid in id_map:
                hybrid_scores[id_map[mid]] = -1

        # Rank and collect results
        top_indices = np.argsort(hybrid_scores)[::-1][:n * 2]  # Get extra to filter
        results = []
        for i in top_indices:
            if len(results) >= n:
                break
            movie = all_movies[i]
            mid = movie.get("id")
            if mid not in seed_ids and hybrid_scores[i] > 0:
                # Attach score for debugging (stripped before JSON response)
                movie["_score"] = round(float(hybrid_scores[i]), 4)
                movie["_content"] = round(float(content_norm[i]), 4)
                movie["_metadata"] = round(float(metadata_sims[i]), 4)
                movie["_quality"] = round(float(quality_scores[i]), 4)
                results.append(movie)

        return results

    except Exception as e:
        logger.warning(f"Hybrid recommend error: {e}")
        return []


def recommend_similar(movie, pool, n=12):
    """Recommend movies similar to a single movie from a pool."""
    return recommend_from_pool([movie], pool, n=n)

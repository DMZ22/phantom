import json
import random
import string
import hashlib
from datetime import datetime, timedelta

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Avg, Count

from .models import Review, Booking
from .services.tmdb import tmdb
from .services.chat import chat_service


# ---------------------------------------------------------------------------
# Region / theater config
# ---------------------------------------------------------------------------

THEATERS_BY_REGION = {
    "IN": {
        "theaters": [
            {"name": "PVR INOX Nexus", "screens": ["Audi 1", "Audi 2", "IMAX", "4DX"]},
            {"name": "Cinepolis DLF", "screens": ["Screen 1", "Screen 2", "MX4D"]},
            {"name": "Miraj Cinemas", "screens": ["Gold Class", "Screen 1", "Screen 2"]},
            {"name": "INOX Megaplex", "screens": ["Insignia", "IMAX", "Screen 3"]},
        ],
        "currency": "INR",
        "symbol": "\u20b9",
        "base_price": 250,
        "premium_multiplier": 1.8,
        "times": ["10:00 AM", "01:15 PM", "04:30 PM", "07:45 PM", "10:30 PM"],
    },
    "US": {
        "theaters": [
            {"name": "AMC Empire 25", "screens": ["Dolby Cinema", "IMAX", "Screen 5", "Screen 12"]},
            {"name": "Regal Union Square", "screens": ["RPX", "Screen 1", "Screen 7"]},
            {"name": "Cinemark XD", "screens": ["XD", "Screen 3", "Screen 8"]},
            {"name": "Alamo Drafthouse", "screens": ["Main", "Loft", "Screen 2"]},
        ],
        "currency": "USD",
        "symbol": "$",
        "base_price": 14,
        "premium_multiplier": 1.6,
        "times": ["10:30 AM", "01:00 PM", "04:15 PM", "07:30 PM", "10:00 PM"],
    },
    "GB": {
        "theaters": [
            {"name": "Odeon Luxe Leicester Sq", "screens": ["Dolby Cinema", "IMAX", "Screen 2"]},
            {"name": "Cineworld Leicester Sq", "screens": ["4DX", "ScreenX", "IMAX", "Screen 5"]},
            {"name": "Curzon Soho", "screens": ["Screen 1", "Screen 2"]},
            {"name": "Picturehouse Central", "screens": ["Main", "Screen 2"]},
        ],
        "currency": "GBP",
        "symbol": "\u00a3",
        "base_price": 12,
        "premium_multiplier": 1.7,
        "times": ["11:00 AM", "02:00 PM", "05:15 PM", "08:00 PM", "10:45 PM"],
    },
    "JP": {
        "theaters": [
            {"name": "TOHO Cinemas Shinjuku", "screens": ["IMAX", "MX4D", "Screen 1", "Screen 5"]},
            {"name": "109 Cinemas Premium", "screens": ["IMAX", "4DX", "Screen 3"]},
            {"name": "Wald 9 Shinjuku", "screens": ["Screen 1", "Screen 2", "Screen 7"]},
        ],
        "currency": "JPY",
        "symbol": "\u00a5",
        "base_price": 1900,
        "premium_multiplier": 1.5,
        "times": ["10:00 AM", "12:45 PM", "03:30 PM", "06:15 PM", "09:00 PM"],
    },
}

EVENTS_BY_REGION = {
    "IN": [
        {
            "id": 1, "title": "Mughal-E-Azam: The Musical",
            "category": "Theatre", "date": "Apr 12, 2026",
            "venue": "NCPA, Mumbai", "price": "\u20b91,500 onwards",
            "image": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400",
            "description": "A spectacular musical adaptation of the iconic Bollywood classic.",
        },
        {
            "id": 2, "title": "Zakir Khan Live - Tathastu",
            "category": "Comedy", "date": "Apr 18, 2026",
            "venue": "JLN Stadium, Delhi", "price": "\u20b9999 onwards",
            "image": "https://images.unsplash.com/photo-1585699324551-f6c309eedeca?w=400",
            "description": "Zakir Khan's latest stand-up special exploring life and dreams.",
        },
        {
            "id": 3, "title": "Arijit Singh Live in Concert",
            "category": "Music", "date": "May 3, 2026",
            "venue": "DY Patil Stadium, Mumbai", "price": "\u20b92,000 onwards",
            "image": "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=400",
            "description": "The voice of Bollywood performs his greatest hits live.",
        },
        {
            "id": 4, "title": "AP Dhillon Live Tour",
            "category": "Music", "date": "May 10, 2026",
            "venue": "Jawaharlal Nehru Stadium, Delhi", "price": "\u20b93,500 onwards",
            "image": "https://images.unsplash.com/photo-1470229722913-7c0e2dbbafd3?w=400",
            "description": "The Punjabi music sensation's electrifying India tour.",
        },
        {
            "id": 5, "title": "Biswa Kalyan Rath - Sahi Mein",
            "category": "Comedy", "date": "May 17, 2026",
            "venue": "St. Andrew's Auditorium, Mumbai", "price": "\u20b9799 onwards",
            "image": "https://images.unsplash.com/photo-1527224857830-43a7acc85260?w=400",
            "description": "Biswa's brand-new hour of observational comedy.",
        },
        {
            "id": 6, "title": "Indian Classical Music Festival",
            "category": "Music", "date": "Jun 1, 2026",
            "venue": "Shanmukhananda Hall, Mumbai", "price": "\u20b9500 onwards",
            "image": "https://images.unsplash.com/photo-1514320291840-2e0a9bf2a9ae?w=400",
            "description": "Featuring Zakir Hussain, Amjad Ali Khan and other maestros.",
        },
        {
            "id": 7, "title": "Prateek Kuhad - Silhouettes Tour",
            "category": "Music", "date": "Jun 14, 2026",
            "venue": "Phoenix Marketcity, Bangalore", "price": "\u20b91,200 onwards",
            "image": "https://images.unsplash.com/photo-1501612780327-45045538702b?w=400",
            "description": "Indie-folk sensation Prateek Kuhad performs his latest album.",
        },
        {
            "id": 8, "title": "Comic Con India 2026",
            "category": "Festival", "date": "Jul 5-7, 2026",
            "venue": "NESCO, Mumbai", "price": "\u20b9899 onwards",
            "image": "https://images.unsplash.com/photo-1612036782180-6f0b6cd846fe?w=400",
            "description": "India's biggest pop culture convention with celebrity panels.",
        },
        {
            "id": 9, "title": "Sunburn Arena ft. Martin Garrix",
            "category": "Music", "date": "Jul 19, 2026",
            "venue": "Mahalaxmi Racecourse, Mumbai", "price": "\u20b92,500 onwards",
            "image": "https://images.unsplash.com/photo-1574391884720-bbc3740c59d1?w=400",
            "description": "Asia's biggest EDM festival featuring global DJs.",
        },
    ],
    "US": [
        {
            "id": 1, "title": "Hamilton - Broadway",
            "category": "Theatre", "date": "Apr 15, 2026",
            "venue": "Richard Rodgers Theatre, NYC", "price": "$199 onwards",
            "image": "https://images.unsplash.com/photo-1503095396549-807759245b35?w=400",
            "description": "The revolutionary musical that changed Broadway forever.",
        },
        {
            "id": 2, "title": "Beyonce - Renaissance World Tour",
            "category": "Music", "date": "May 1, 2026",
            "venue": "SoFi Stadium, LA", "price": "$150 onwards",
            "image": "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=400",
            "description": "Queen Bey brings her spectacular Renaissance show.",
        },
        {
            "id": 3, "title": "Dave Chappelle Live",
            "category": "Comedy", "date": "May 10, 2026",
            "venue": "Madison Square Garden, NYC", "price": "$120 onwards",
            "image": "https://images.unsplash.com/photo-1585699324551-f6c309eedeca?w=400",
            "description": "The legendary comedian's intimate evening of stand-up.",
        },
        {
            "id": 4, "title": "Wicked - The Musical",
            "category": "Theatre", "date": "May 20, 2026",
            "venue": "Gershwin Theatre, NYC", "price": "$175 onwards",
            "image": "https://images.unsplash.com/photo-1507676184212-d03ab07a01bf?w=400",
            "description": "The untold story of the witches of Oz continues to enchant.",
        },
        {
            "id": 5, "title": "Taylor Swift - Eras Tour II",
            "category": "Music", "date": "Jun 5, 2026",
            "venue": "MetLife Stadium, NJ", "price": "$250 onwards",
            "image": "https://images.unsplash.com/photo-1470229722913-7c0e2dbbafd3?w=400",
            "description": "The global phenomenon returns with new eras and surprises.",
        },
        {
            "id": 6, "title": "John Mulaney - Back in Town",
            "category": "Comedy", "date": "Jun 20, 2026",
            "venue": "The Forum, LA", "price": "$85 onwards",
            "image": "https://images.unsplash.com/photo-1527224857830-43a7acc85260?w=400",
            "description": "John Mulaney's hilarious new touring show.",
        },
        {
            "id": 7, "title": "San Diego Comic-Con 2026",
            "category": "Festival", "date": "Jul 24-27, 2026",
            "venue": "San Diego Convention Center", "price": "$65 onwards",
            "image": "https://images.unsplash.com/photo-1612036782180-6f0b6cd846fe?w=400",
            "description": "The world's premier comic and entertainment convention.",
        },
        {
            "id": 8, "title": "Kendrick Lamar - GNX Tour",
            "category": "Music", "date": "Aug 2, 2026",
            "venue": "United Center, Chicago", "price": "$130 onwards",
            "image": "https://images.unsplash.com/photo-1501612780327-45045538702b?w=400",
            "description": "Kendrick Lamar's arena tour supporting his latest album.",
        },
    ],
    "GB": [
        {
            "id": 1, "title": "Les Miserables - West End",
            "category": "Theatre", "date": "Apr 12, 2026",
            "venue": "Sondheim Theatre, London", "price": "\u00a335 onwards",
            "image": "https://images.unsplash.com/photo-1503095396549-807759245b35?w=400",
            "description": "The world's longest-running musical in its London home.",
        },
        {
            "id": 2, "title": "Coldplay - Music of the Spheres",
            "category": "Music", "date": "May 8, 2026",
            "venue": "Wembley Stadium, London", "price": "\u00a375 onwards",
            "image": "https://images.unsplash.com/photo-1470229722913-7c0e2dbbafd3?w=400",
            "description": "Coldplay's spectacular world tour comes home to Wembley.",
        },
        {
            "id": 3, "title": "Hamlet - Shakespeare's Globe",
            "category": "Theatre", "date": "May 22, 2026",
            "venue": "Shakespeare's Globe, London", "price": "\u00a325 onwards",
            "image": "https://images.unsplash.com/photo-1507676184212-d03ab07a01bf?w=400",
            "description": "A fresh new production of Shakespeare's greatest tragedy.",
        },
        {
            "id": 4, "title": "Jimmy Carr - Laughs Funny",
            "category": "Comedy", "date": "Jun 5, 2026",
            "venue": "O2 Arena, London", "price": "\u00a340 onwards",
            "image": "https://images.unsplash.com/photo-1527224857830-43a7acc85260?w=400",
            "description": "Jimmy Carr's brand new show of sharp one-liners.",
        },
        {
            "id": 5, "title": "Adele - Weekends with Adele UK",
            "category": "Music", "date": "Jun 20, 2026",
            "venue": "The O2 Arena, London", "price": "\u00a395 onwards",
            "image": "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=400",
            "description": "Adele's long-awaited UK residency concert series.",
        },
        {
            "id": 6, "title": "Edinburgh Fringe Festival",
            "category": "Festival", "date": "Aug 1-25, 2026",
            "venue": "Various Venues, Edinburgh", "price": "\u00a310 onwards",
            "image": "https://images.unsplash.com/photo-1514320291840-2e0a9bf2a9ae?w=400",
            "description": "The world's largest arts festival with thousands of shows.",
        },
        {
            "id": 7, "title": "The Phantom of the Opera",
            "category": "Theatre", "date": "Jul 10, 2026",
            "venue": "Her Majesty's Theatre, London", "price": "\u00a330 onwards",
            "image": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400",
            "description": "Andrew Lloyd Webber's iconic masterpiece returns to the West End.",
        },
        {
            "id": 8, "title": "MCM London Comic Con",
            "category": "Festival", "date": "Oct 24-26, 2026",
            "venue": "ExCeL London", "price": "\u00a320 onwards",
            "image": "https://images.unsplash.com/photo-1612036782180-6f0b6cd846fe?w=400",
            "description": "The UK's biggest pop culture and comic convention.",
        },
    ],
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _get_region(request):
    return request.GET.get("region", "US").upper()


def _generate_booking_code():
    chars = string.ascii_uppercase + string.digits
    code = "PH-" + "".join(random.choices(chars, k=6))
    return code


def _generate_showtimes(movie_id, region="US"):
    config = THEATERS_BY_REGION.get(region, THEATERS_BY_REGION["US"])
    today = datetime.now()
    showtimes = []

    for day_offset in range(5):
        date = today + timedelta(days=day_offset)
        date_str = date.strftime("%a, %b %d")

        for theater in config["theaters"]:
            # Deterministic seed for consistent showtimes
            seed_str = f"{movie_id}-{theater['name']}-{date_str}"
            seed_val = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
            rng = random.Random(seed_val)

            available_times = rng.sample(config["times"], min(len(config["times"]), rng.randint(2, len(config["times"]))))
            available_times.sort()

            for screen in theater["screens"]:
                is_premium = any(tag in screen.upper() for tag in ["IMAX", "4DX", "DOLBY", "MX4D", "XD", "RPX", "INSIGNIA", "GOLD", "SCREENX"])
                price = config["base_price"] * config["premium_multiplier"] if is_premium else config["base_price"]

                screen_times = rng.sample(available_times, min(len(available_times), rng.randint(1, len(available_times))))
                screen_times.sort()

                for time_str in screen_times:
                    # Generate seat availability
                    total_seats = rng.randint(80, 200)
                    booked_pct = rng.uniform(0.2, 0.85)
                    available_seats = int(total_seats * (1 - booked_pct))

                    showtimes.append({
                        "id": f"{movie_id}-{theater['name']}-{screen}-{date_str}-{time_str}".replace(" ", "_"),
                        "theater": theater["name"],
                        "screen": screen,
                        "date": date_str,
                        "time": time_str,
                        "price": round(price, 2),
                        "currency": config["currency"],
                        "symbol": config["symbol"],
                        "available_seats": available_seats,
                        "total_seats": total_seats,
                        "is_premium": is_premium,
                    })

    return showtimes


# ---------------------------------------------------------------------------
# PAGE VIEWS
# ---------------------------------------------------------------------------

def home(request):
    region = _get_region(request)

    try:
        trending = tmdb.get_trending(region=region)
    except Exception:
        trending = {}

    try:
        top_rated = tmdb.get_top_rated(region=region)
    except Exception:
        top_rated = {}

    try:
        now_playing = tmdb.get_now_playing(region=region)
    except Exception:
        now_playing = {}

    try:
        popular = tmdb.get_popular(region=region)
    except Exception:
        popular = {}

    trending_results = trending.get("results", [])
    hero = trending_results[:5]

    context = {
        "hero_json": json.dumps(hero),
        "trending_json": json.dumps(trending_results),
        "top_rated_json": json.dumps(top_rated.get("results", [])),
        "now_playing_json": json.dumps(now_playing.get("results", [])),
        "popular_json": json.dumps(popular.get("results", [])),
        "region": region,
    }
    return render(request, "movies/home.html", context)


def movie_detail(request, movie_id):
    region = _get_region(request)

    try:
        movie = tmdb.get_movie_details(movie_id)
    except Exception:
        movie = {}

    if not movie:
        movie = {"id": movie_id, "title": "Movie Not Found", "overview": "", "genres": [], "credits": {"cast": []}}

    # Extract trailer key
    trailer_key = ""
    videos = movie.get("videos", {}).get("results", [])
    for v in videos:
        if v.get("type") == "Trailer" and v.get("site") == "YouTube":
            trailer_key = v["key"]
            break

    # Extract watch providers
    watch_providers = movie.get("watch/providers", {}).get("results", {})

    # Recommendations (movies from same genre, excluding current)
    recommendations = []
    if movie.get("genres"):
        genre_id = movie["genres"][0]["id"]
        try:
            rec_data = tmdb.get_by_genre(genre_id, region=region)
            recs = rec_data.get("results", [])
            recommendations = [r for r in recs if r.get("id") != movie_id][:12]
        except Exception:
            recommendations = []

    context = {
        "movie": movie,
        "trailer_key": trailer_key,
        "watch_providers_json": json.dumps(watch_providers),
        "recommendations_json": json.dumps(recommendations),
        "region": region,
    }
    return render(request, "movies/movie_detail.html", context)


def booking(request, movie_id):
    region = _get_region(request)

    try:
        movie = tmdb.get_movie_details(movie_id)
    except Exception:
        movie = {}

    if not movie:
        movie = {"id": movie_id, "title": "Movie", "genres": []}

    showtimes = _generate_showtimes(movie_id, region)

    context = {
        "movie": movie,
        "showtimes_json": json.dumps(showtimes),
        "region": region,
    }
    return render(request, "movies/booking.html", context)


def browse(request):
    region = _get_region(request)

    try:
        genres = tmdb.get_genres()
    except Exception:
        genres = {}

    try:
        popular = tmdb.get_popular(region=region)
    except Exception:
        popular = {}

    context = {
        "genres_json": json.dumps(genres.get("genres", [])),
        "movies_json": json.dumps(popular.get("results", [])),
        "region": region,
    }
    return render(request, "movies/browse.html", context)


def search_page(request):
    region = _get_region(request)
    query = request.GET.get("q", "")
    results = []

    if query:
        try:
            data = tmdb.search_movies(query, region=region)
            results = data.get("results", [])
        except Exception:
            results = []

    context = {
        "query": query,
        "results_json": json.dumps(results),
        "total_results": len(results),
        "region": region,
    }
    return render(request, "movies/search.html", context)


def events(request):
    region = _get_region(request)
    region_events = EVENTS_BY_REGION.get(region, EVENTS_BY_REGION.get("US", []))

    context = {
        "events_json": json.dumps(region_events),
        "region": region,
    }
    return render(request, "movies/events.html", context)


# ---------------------------------------------------------------------------
# API VIEWS
# ---------------------------------------------------------------------------

def api_movies(request, category):
    region = request.GET.get("region", "US")
    page = int(request.GET.get("page", 1))
    window = request.GET.get("window", "week")

    category_map = {
        "trending": lambda: tmdb.get_trending(page=page, region=region, window=window),
        "popularity": lambda: tmdb.get_popular(page=page, region=region),
        "popular": lambda: tmdb.get_popular(page=page, region=region),
        "top_rated": lambda: tmdb.get_top_rated(page=page, region=region),
        "now_playing": lambda: tmdb.get_now_playing(page=page, region=region),
    }

    fetcher = category_map.get(category)
    if not fetcher:
        return JsonResponse({"error": f"Unknown category: {category}"}, status=400)

    try:
        data = fetcher()
    except Exception:
        data = {}

    return JsonResponse(data, safe=False)


def api_search_movies(request):
    query = request.GET.get("q", "")
    region = request.GET.get("region", "US")
    page = int(request.GET.get("page", 1))

    if not query:
        return JsonResponse({"results": [], "total_results": 0})

    try:
        data = tmdb.search_movies(query, page=page, region=region)
    except Exception:
        data = {"results": [], "total_results": 0}

    return JsonResponse(data, safe=False)


def api_genres(request):
    try:
        data = tmdb.get_genres()
    except Exception:
        data = {}

    return JsonResponse({"genres": data.get("genres", [])})


def api_genre(request, genre_id):
    region = request.GET.get("region", "US")
    page = int(request.GET.get("page", 1))

    try:
        data = tmdb.get_by_genre(genre_id, page=page, region=region)
    except Exception:
        data = {}

    return JsonResponse(data, safe=False)


def api_reviews(request, movie_id):
    if request.method == "POST":
        return _create_review(request, movie_id)

    reviews = list(
        Review.objects.filter(movie_id=movie_id).values(
            "id", "rating", "content", "author", "created_at"
        )[:50]
    )
    for r in reviews:
        r["created_at"] = r["created_at"].isoformat()

    return JsonResponse({"reviews": reviews})


@csrf_exempt
def _create_review(request, movie_id):
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    rating = body.get("rating")
    content = body.get("content", "")
    author = body.get("author", "Ghost Viewer") or "Ghost Viewer"

    if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
        return JsonResponse({"error": "Rating must be 1-5"}, status=400)

    review = Review.objects.create(
        movie_id=movie_id,
        rating=rating,
        content=content,
        author=author,
    )

    return JsonResponse({
        "id": review.id,
        "movie_id": review.movie_id,
        "rating": review.rating,
        "content": review.content,
        "author": review.author,
        "created_at": review.created_at.isoformat(),
    }, status=201)


# Make the POST api_reviews endpoint csrf_exempt
api_reviews = csrf_exempt(api_reviews)


def api_review_stats(request, movie_id):
    stats = Review.objects.filter(movie_id=movie_id).aggregate(
        avg_rating=Avg("rating"), count=Count("id")
    )
    distribution = {}
    for i in range(1, 6):
        distribution[str(i)] = Review.objects.filter(movie_id=movie_id, rating=i).count()

    return JsonResponse({
        "avg_rating": round(stats["avg_rating"], 1) if stats["avg_rating"] else 0,
        "count": stats["count"] or 0,
        "distribution": distribution,
    })


def api_showtimes(request, movie_id):
    region = request.GET.get("region", "US")
    showtimes = _generate_showtimes(movie_id, region)
    return JsonResponse({"showtimes": showtimes})


@csrf_exempt
def api_create_booking(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    movie_id = body.get("movie_id")
    movie_title = body.get("movie_title", "Unknown Movie")
    showtime = body.get("showtime", "")
    seats = body.get("seats", [])
    total_price = body.get("total_price", 0)

    if not movie_id:
        return JsonResponse({"error": "movie_id required"}, status=400)
    if not seats:
        return JsonResponse({"error": "seats required"}, status=400)

    booking_code = _generate_booking_code()
    # Ensure uniqueness
    while Booking.objects.filter(booking_code=booking_code).exists():
        booking_code = _generate_booking_code()

    booking_obj = Booking.objects.create(
        booking_code=booking_code,
        movie_id=movie_id,
        movie_title=movie_title,
        showtime=showtime,
        seats=seats,
        total_price=float(total_price),
    )

    return JsonResponse({
        "booking_code": booking_obj.booking_code,
        "movie_id": booking_obj.movie_id,
        "movie_title": booking_obj.movie_title,
        "showtime": booking_obj.showtime,
        "seats": booking_obj.seats,
        "total_price": booking_obj.total_price,
        "status": booking_obj.status,
        "created_at": booking_obj.created_at.isoformat(),
    }, status=201)


@csrf_exempt
def api_chat(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    movie_id = body.get("movie_id")
    movie_title = body.get("movie_title", "")
    movie_overview = body.get("movie_overview", "")
    messages = body.get("messages", [])

    if not messages:
        return JsonResponse({"error": "messages required"}, status=400)

    response_text = chat_service.chat(movie_id, movie_title, movie_overview, messages)

    return JsonResponse({"response": response_text})

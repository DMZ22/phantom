import json
import logging
import random
import string
import hashlib
from datetime import datetime, timedelta

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Avg, Count

logger = logging.getLogger(__name__)

from .models import Review, Booking, UserProfile
from .services.tmdb import tmdb
from .services.chat import chat_service
from .services.recommender import recommend_from_pool


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
        {"id": 1, "title": "Mughal-E-Azam: The Musical", "category": "Theatre", "date": "Apr 12, 2026", "time": "7:00 PM", "duration": "2h 45m", "venue": "NCPA, Mumbai", "price": "\u20b91,500", "price_usd": 18, "image": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400", "description": "A spectacular musical adaptation of the iconic Bollywood classic with lavish sets and costumes."},
        {"id": 2, "title": "Zakir Khan Live - Tathastu", "category": "Comedy", "date": "Apr 18, 2026", "time": "8:00 PM", "duration": "2h", "venue": "JLN Stadium, Delhi", "price": "\u20b9999", "price_usd": 12, "image": "https://images.unsplash.com/photo-1585699324551-f6c309eedeca?w=400", "description": "Zakir Khan's latest stand-up special exploring life, dreams, and everything in between."},
        {"id": 3, "title": "Arijit Singh Live in Concert", "category": "Music", "date": "May 3, 2026", "time": "7:30 PM", "duration": "3h", "venue": "DY Patil Stadium, Mumbai", "price": "\u20b92,000", "price_usd": 24, "image": "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=400", "description": "The voice of Bollywood performs his greatest hits live with a full orchestra."},
        {"id": 4, "title": "AP Dhillon Live Tour", "category": "Music", "date": "May 10, 2026", "time": "8:00 PM", "duration": "2h 30m", "venue": "Jawaharlal Nehru Stadium, Delhi", "price": "\u20b93,500", "price_usd": 42, "image": "https://images.unsplash.com/photo-1470229722913-7c0e2dbbafd3?w=400", "description": "The Punjabi music sensation's electrifying India tour with special guests."},
        {"id": 5, "title": "Biswa Kalyan Rath - Sahi Mein", "category": "Comedy", "date": "May 17, 2026", "time": "8:30 PM", "duration": "1h 30m", "venue": "St. Andrew's Auditorium, Mumbai", "price": "\u20b9799", "price_usd": 10, "image": "https://images.unsplash.com/photo-1527224857830-43a7acc85260?w=400", "description": "Biswa's brand-new hour of razor-sharp observational comedy."},
        {"id": 6, "title": "Indian Classical Music Festival", "category": "Music", "date": "Jun 1, 2026", "time": "6:00 PM", "duration": "4h", "venue": "Shanmukhananda Hall, Mumbai", "price": "\u20b9500", "price_usd": 6, "image": "https://images.unsplash.com/photo-1514320291840-2e0a9bf2a9ae?w=400", "description": "Featuring Zakir Hussain, Amjad Ali Khan and other maestros in a night of ragas."},
        {"id": 7, "title": "Prateek Kuhad - Silhouettes Tour", "category": "Music", "date": "Jun 14, 2026", "time": "7:30 PM", "duration": "2h", "venue": "Phoenix Marketcity, Bangalore", "price": "\u20b91,200", "price_usd": 14, "image": "https://images.unsplash.com/photo-1501612780327-45045538702b?w=400", "description": "Indie-folk sensation Prateek Kuhad performs his latest album live."},
        {"id": 8, "title": "Comic Con India 2026", "category": "Festival", "date": "Jul 5-7, 2026", "time": "10:00 AM", "duration": "All Day", "venue": "NESCO, Mumbai", "price": "\u20b9899", "price_usd": 11, "image": "https://images.unsplash.com/photo-1612036782180-6f0b6cd846fe?w=400", "description": "India's biggest pop culture convention with celebrity panels and cosplay."},
        {"id": 9, "title": "Sunburn Arena ft. Martin Garrix", "category": "Music", "date": "Jul 19, 2026", "time": "4:00 PM", "duration": "8h", "venue": "Mahalaxmi Racecourse, Mumbai", "price": "\u20b92,500", "price_usd": 30, "image": "https://images.unsplash.com/photo-1574391884720-bbc3740c59d1?w=400", "description": "Asia's biggest EDM festival featuring global DJs and spectacular production."},
    ],
    "US": [
        {"id": 1, "title": "Hamilton - Broadway", "category": "Theatre", "date": "Apr 15, 2026", "time": "7:00 PM", "duration": "2h 45m", "venue": "Richard Rodgers Theatre, NYC", "price": "$199", "price_usd": 199, "image": "https://images.unsplash.com/photo-1503095396549-807759245b35?w=400", "description": "The revolutionary musical that changed Broadway forever."},
        {"id": 2, "title": "Beyonce - Renaissance World Tour", "category": "Music", "date": "May 1, 2026", "time": "8:00 PM", "duration": "3h", "venue": "SoFi Stadium, LA", "price": "$150", "price_usd": 150, "image": "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=400", "description": "Queen Bey brings her spectacular Renaissance show to LA."},
        {"id": 3, "title": "Dave Chappelle Live", "category": "Comedy", "date": "May 10, 2026", "time": "9:00 PM", "duration": "2h", "venue": "Madison Square Garden, NYC", "price": "$120", "price_usd": 120, "image": "https://images.unsplash.com/photo-1585699324551-f6c309eedeca?w=400", "description": "The legendary comedian's intimate evening of stand-up comedy."},
        {"id": 4, "title": "Wicked - The Musical", "category": "Theatre", "date": "May 20, 2026", "time": "7:00 PM", "duration": "2h 30m", "venue": "Gershwin Theatre, NYC", "price": "$175", "price_usd": 175, "image": "https://images.unsplash.com/photo-1507676184212-d03ab07a01bf?w=400", "description": "The untold story of the witches of Oz continues to enchant audiences."},
        {"id": 5, "title": "Taylor Swift - Eras Tour II", "category": "Music", "date": "Jun 5, 2026", "time": "7:00 PM", "duration": "3h 30m", "venue": "MetLife Stadium, NJ", "price": "$250", "price_usd": 250, "image": "https://images.unsplash.com/photo-1470229722913-7c0e2dbbafd3?w=400", "description": "The global phenomenon returns with new eras and surprises."},
        {"id": 6, "title": "John Mulaney - Back in Town", "category": "Comedy", "date": "Jun 20, 2026", "time": "8:00 PM", "duration": "1h 30m", "venue": "The Forum, LA", "price": "$85", "price_usd": 85, "image": "https://images.unsplash.com/photo-1527224857830-43a7acc85260?w=400", "description": "John Mulaney's hilarious new touring show full of surprises."},
        {"id": 7, "title": "San Diego Comic-Con 2026", "category": "Festival", "date": "Jul 24-27, 2026", "time": "10:00 AM", "duration": "All Day", "venue": "San Diego Convention Center", "price": "$65", "price_usd": 65, "image": "https://images.unsplash.com/photo-1612036782180-6f0b6cd846fe?w=400", "description": "The world's premier comic and entertainment convention."},
        {"id": 8, "title": "Kendrick Lamar - GNX Tour", "category": "Music", "date": "Aug 2, 2026", "time": "8:00 PM", "duration": "2h 30m", "venue": "United Center, Chicago", "price": "$130", "price_usd": 130, "image": "https://images.unsplash.com/photo-1501612780327-45045538702b?w=400", "description": "Kendrick Lamar's arena tour supporting his latest album."},
    ],
    "GB": [
        {"id": 1, "title": "Les Miserables - West End", "category": "Theatre", "date": "Apr 12, 2026", "time": "7:30 PM", "duration": "2h 50m", "venue": "Sondheim Theatre, London", "price": "\u00a335", "price_usd": 44, "image": "https://images.unsplash.com/photo-1503095396549-807759245b35?w=400", "description": "The world's longest-running musical in its London home."},
        {"id": 2, "title": "Coldplay - Music of the Spheres", "category": "Music", "date": "May 8, 2026", "time": "7:00 PM", "duration": "2h 30m", "venue": "Wembley Stadium, London", "price": "\u00a375", "price_usd": 95, "image": "https://images.unsplash.com/photo-1470229722913-7c0e2dbbafd3?w=400", "description": "Coldplay's spectacular world tour comes home to Wembley."},
        {"id": 3, "title": "Hamlet - Shakespeare's Globe", "category": "Theatre", "date": "May 22, 2026", "time": "7:30 PM", "duration": "3h", "venue": "Shakespeare's Globe, London", "price": "\u00a325", "price_usd": 32, "image": "https://images.unsplash.com/photo-1507676184212-d03ab07a01bf?w=400", "description": "A fresh new production of Shakespeare's greatest tragedy."},
        {"id": 4, "title": "Jimmy Carr - Laughs Funny", "category": "Comedy", "date": "Jun 5, 2026", "time": "8:00 PM", "duration": "2h", "venue": "O2 Arena, London", "price": "\u00a340", "price_usd": 51, "image": "https://images.unsplash.com/photo-1527224857830-43a7acc85260?w=400", "description": "Jimmy Carr's brand new show of sharp one-liners and dark humour."},
        {"id": 5, "title": "Adele - Weekends with Adele UK", "category": "Music", "date": "Jun 20, 2026", "time": "8:00 PM", "duration": "2h 15m", "venue": "The O2 Arena, London", "price": "\u00a395", "price_usd": 120, "image": "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=400", "description": "Adele's long-awaited UK residency concert series."},
        {"id": 6, "title": "Edinburgh Fringe Festival", "category": "Festival", "date": "Aug 1-25, 2026", "time": "Various", "duration": "All Day", "venue": "Various Venues, Edinburgh", "price": "\u00a310", "price_usd": 13, "image": "https://images.unsplash.com/photo-1514320291840-2e0a9bf2a9ae?w=400", "description": "The world's largest arts festival with thousands of shows."},
        {"id": 7, "title": "The Phantom of the Opera", "category": "Theatre", "date": "Jul 10, 2026", "time": "7:30 PM", "duration": "2h 30m", "venue": "Her Majesty's Theatre, London", "price": "\u00a330", "price_usd": 38, "image": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400", "description": "Andrew Lloyd Webber's iconic masterpiece returns to the West End."},
        {"id": 8, "title": "MCM London Comic Con", "category": "Festival", "date": "Oct 24-26, 2026", "time": "10:00 AM", "duration": "All Day", "venue": "ExCeL London", "price": "\u00a320", "price_usd": 25, "image": "https://images.unsplash.com/photo-1612036782180-6f0b6cd846fe?w=400", "description": "The UK's biggest pop culture and comic convention."},
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

@ensure_csrf_cookie
def home(request):
    region = _get_region(request)

    trending = tmdb.get_trending(region=region)
    top_rated = tmdb.get_top_rated(region=region)
    now_playing = tmdb.get_now_playing(region=region)
    popular = tmdb.get_popular(region=region)

    # Check if any API calls had errors
    api_error = any(tmdb.is_error(d) for d in [trending, top_rated, now_playing, popular])

    trending_results = trending.get("results", [])
    hero = trending_results[:5]

    # ML-powered "Recommended For You" — blend trending + popular via TF-IDF
    recommended = []
    all_pool = trending_results + popular.get("results", []) + now_playing.get("results", [])
    if len(all_pool) >= 10:
        try:
            seeds = (top_rated.get("results", []) or trending_results)[:5]
            recommended = recommend_from_pool(seeds, all_pool, n=20)
            seen_ids = set()
            deduped = []
            for m in recommended:
                mid = m.get("id")
                if mid and mid not in seen_ids:
                    seen_ids.add(mid)
                    deduped.append(m)
            recommended = deduped[:16]
        except Exception as e:
            logger.warning(f"Recommender exception: {e}")
            recommended = []

    context = {
        "hero_json": json.dumps(hero),
        "trending_json": json.dumps(trending_results),
        "top_rated_json": json.dumps(top_rated.get("results", [])),
        "now_playing_json": json.dumps(now_playing.get("results", [])),
        "popular_json": json.dumps(popular.get("results", [])),
        "recommended_json": json.dumps(recommended),
        "api_error": api_error,
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

    # Recommendations — TF-IDF powered, multi-source pool
    recommendations = []
    try:
        pool = []
        # Get movies from same genre(s)
        if movie.get("genres"):
            for genre in movie["genres"][:2]:
                try:
                    rec_data = tmdb.get_by_genre(genre["id"], region=region)
                    pool += rec_data.get("results", [])
                except Exception:
                    pass
        # Add popular/trending for diversity
        for fetch_fn in [
            lambda: tmdb.get_popular(region=region),
            lambda: tmdb.get_trending(region=region, window="week"),
        ]:
            try:
                pool += fetch_fn().get("results", [])
            except Exception:
                pass
        # Remove the current movie from pool
        pool = [r for r in pool if r.get("id") != movie_id]
        # Deduplicate pool
        seen = set()
        deduped_pool = []
        for m in pool:
            if m.get("id") not in seen:
                seen.add(m.get("id"))
                deduped_pool.append(m)
        pool = deduped_pool

        # ML recommendations
        if len(pool) >= 5:
            try:
                recommendations = recommend_from_pool([movie], pool, n=12)
            except Exception:
                pass

        # Fallback to genre match
        if not recommendations:
            recommendations = pool[:12]
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
    search_recs = []

    total_results = 0
    total_pages = 1

    if query:
        try:
            data = tmdb.search_movies(query, region=region)
            results = data.get("results", [])
            total_results = data.get("total_results", len(results))
            total_pages = data.get("total_pages", 1)
        except Exception:
            results = []

        # Generate recommendations based on search results
        if len(results) >= 3:
            try:
                pool = []
                for fetch_fn in [
                    lambda: tmdb.get_popular(region=region),
                    lambda: tmdb.get_trending(region=region, window="week"),
                    lambda: tmdb.get_now_playing(region=region),
                ]:
                    try:
                        pool += fetch_fn().get("results", [])
                    except Exception:
                        pass
                if len(pool) < 10:
                    pool += results[3:]
                # Deduplicate pool
                seen_ids = set()
                deduped = []
                for m in pool:
                    mid = m.get("id")
                    if mid and mid not in seen_ids:
                        seen_ids.add(mid)
                        deduped.append(m)
                pool = deduped
                if pool:
                    seeds = results[:3]
                    search_recs = recommend_from_pool(seeds, pool, n=12)
                    result_ids = {m.get("id") for m in results}
                    search_recs = [m for m in search_recs if m.get("id") not in result_ids][:10]
            except Exception:
                search_recs = []

    context = {
        "query": query,
        "results_json": json.dumps(results),
        "search_recs_json": json.dumps(search_recs),
        "total_results": total_results,
        "total_pages": total_pages,
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
# AUTH VIEWS
# ---------------------------------------------------------------------------

@ensure_csrf_cookie
def login_page(request):
    if request.user.is_authenticated:
        return redirect("/")
    return render(request, "movies/login.html", {"error": ""})


@csrf_exempt
def api_login(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    mode = body.get("mode", "")  # "credentials" or "guest"

    if mode == "guest":
        mobile = body.get("mobile", "").strip()
        name = body.get("name", "").strip() or "Guest"
        if not mobile or len(mobile) < 6:
            return JsonResponse({"error": "Please enter a valid mobile number"}, status=400)

        # Find or create guest user by mobile
        username = f"guest_{mobile}"
        try:
            profile = UserProfile.objects.get(mobile=mobile, is_guest=True)
            user = profile.user
        except UserProfile.DoesNotExist:
            user = User.objects.create_user(
                username=username,
                password=None,
                first_name=name,
            )
            user.set_unusable_password()
            user.save()
            UserProfile.objects.create(user=user, mobile=mobile, is_guest=True)

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return JsonResponse({
            "success": True,
            "user": {"name": user.first_name or user.username, "is_guest": True},
        })

    elif mode == "credentials":
        username = body.get("username", "").strip()
        password = body.get("password", "")
        if not username or not password:
            return JsonResponse({"error": "Username and password are required"}, status=400)

        user = authenticate(request, username=username, password=password)
        if user is None:
            return JsonResponse({"error": "Invalid username or password"}, status=400)

        login(request, user)
        is_guest = hasattr(user, 'profile') and user.profile.is_guest
        return JsonResponse({
            "success": True,
            "user": {"name": user.first_name or user.username, "is_guest": is_guest},
        })

    elif mode == "register":
        username = body.get("username", "").strip()
        password = body.get("password", "")
        name = body.get("name", "").strip()
        if not username or not password:
            return JsonResponse({"error": "Username and password are required"}, status=400)
        if len(password) < 6:
            return JsonResponse({"error": "Password must be at least 6 characters"}, status=400)
        if User.objects.filter(username=username).exists():
            return JsonResponse({"error": "Username already taken"}, status=400)

        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=name or username,
        )
        UserProfile.objects.create(user=user, is_guest=False)
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return JsonResponse({
            "success": True,
            "user": {"name": user.first_name or user.username, "is_guest": False},
        })

    return JsonResponse({"error": "Invalid mode"}, status=400)


def api_logout(request):
    logout(request)
    return JsonResponse({"success": True})


def api_me(request):
    if request.user.is_authenticated:
        is_guest = hasattr(request.user, 'profile') and request.user.profile.is_guest
        return JsonResponse({
            "authenticated": True,
            "name": request.user.first_name or request.user.username,
            "username": request.user.username,
            "is_guest": is_guest,
        })
    return JsonResponse({"authenticated": False})


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

    data = fetcher()
    if tmdb.is_error(data):
        return JsonResponse({"error": data.get("_message", "API error"), "results": []}, status=503)

    return JsonResponse(data, safe=False)


def api_search_movies(request):
    query = request.GET.get("q", "")
    region = request.GET.get("region", "US")
    page = int(request.GET.get("page", 1))

    if not query:
        return JsonResponse({"results": [], "total_results": 0})

    data = tmdb.search_movies(query, page=page, region=region)
    if tmdb.is_error(data):
        return JsonResponse({
            "error": data.get("_message", "Search failed"),
            "results": [],
            "total_results": 0,
        }, status=503)

    return JsonResponse(data, safe=False)


def api_search_recs(request):
    """Return ML recommendations based on search query results."""
    query = request.GET.get("q", "")
    region = request.GET.get("region", "US")

    if not query:
        return JsonResponse({"recommendations": []})

    try:
        search_data = tmdb.search_movies(query, region=region)
        results = search_data.get("results", [])
        if len(results) < 3:
            return JsonResponse({"recommendations": []})

        # Build pool from multiple sources, gracefully handle failures
        pool = []
        for fetch_fn in [
            lambda: tmdb.get_popular(region=region),
            lambda: tmdb.get_trending(region=region, window="week"),
            lambda: tmdb.get_now_playing(region=region),
        ]:
            try:
                pool += fetch_fn().get("results", [])
            except Exception:
                pass

        # If external pool is too small, use the search results beyond the seeds
        if len(pool) < 10:
            pool += results[3:]

        # Deduplicate pool
        seen_ids = set()
        deduped_pool = []
        for m in pool:
            mid = m.get("id")
            if mid and mid not in seen_ids:
                seen_ids.add(mid)
                deduped_pool.append(m)
        pool = deduped_pool

        if not pool:
            return JsonResponse({"recommendations": []})

        seeds = results[:3]
        recs = recommend_from_pool(seeds, pool, n=12)
        result_ids = {m.get("id") for m in results}
        recs = [m for m in recs if m.get("id") not in result_ids][:10]
        return JsonResponse({"recommendations": recs})
    except Exception:
        return JsonResponse({"recommendations": []})


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
    single_message = body.get("message", "")

    # Support both formats: full messages array or single message
    if not messages and single_message:
        messages = [{"role": "user", "content": single_message}]

    if not messages:
        return JsonResponse({"error": "messages required"}, status=400)

    response_text = chat_service.chat(movie_id, movie_title, movie_overview, messages)

    return JsonResponse({"response": response_text})

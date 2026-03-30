from django.urls import path
from . import views

urlpatterns = [
    # API endpoints (specific paths first, before catch-all patterns)
    path('api/movies/search/', views.api_search_movies, name='api_search_movies'),
    path('api/movies/genres/', views.api_genres, name='api_genres'),
    path('api/movies/genre/<int:genre_id>/', views.api_genre, name='api_genre'),
    path('api/movies/<str:category>/', views.api_movies, name='api_movies'),
    path('api/reviews/<int:movie_id>/stats/', views.api_review_stats, name='api_review_stats'),
    path('api/reviews/<int:movie_id>/', views.api_reviews, name='api_reviews'),
    path('api/bookings/showtimes/<int:movie_id>/', views.api_showtimes, name='api_showtimes'),
    path('api/bookings/create/', views.api_create_booking, name='api_create_booking'),
    path('api/chat/', views.api_chat, name='api_chat'),

    # Page views
    path('', views.home, name='home'),
    path('movie/<int:movie_id>/', views.movie_detail, name='movie_detail'),
    path('book/<int:movie_id>/', views.booking, name='booking'),
    path('movies/', views.browse, name='browse'),
    path('search/', views.search_page, name='search_page'),
    path('events/', views.events, name='events'),
]

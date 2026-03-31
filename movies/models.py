from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    mobile = models.CharField(max_length=20, blank=True)
    is_guest = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        label = "Guest" if self.is_guest else "Member"
        return f"{self.user.username} ({label})"


class Review(models.Model):
    movie_id = models.IntegerField(db_index=True)
    rating = models.IntegerField()
    content = models.TextField()
    author = models.CharField(max_length=100, default="Ghost Viewer")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Review for movie {self.movie_id} by {self.author}"


class Booking(models.Model):
    booking_code = models.CharField(max_length=20, unique=True, db_index=True)
    movie_id = models.IntegerField()
    movie_title = models.CharField(max_length=300)
    showtime = models.CharField(max_length=300)
    seats = models.JSONField(default=list)
    total_price = models.FloatField()
    status = models.CharField(max_length=20, default="confirmed")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking {self.booking_code} - {self.movie_title}"

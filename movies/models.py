from django.db import models


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

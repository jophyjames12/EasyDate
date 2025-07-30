from djongo import models
from django.conf import settings

class CustomUser(models.Model):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)  # Store hashed passwords
    created_at = models.DateTimeField(auto_now_add=True)


    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    friends = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='friends', blank=True)
    
    def add_friend(self, friend):
        self.friends.add(friend)
        self.save()

    def remove_friend(self, friend):
        self.friends.remove(friend)
        self.save()

# Add this new Post model
class Post(models.Model):
    username = models.CharField(max_length=150)
    content = models.TextField(blank=True)
    image = models.CharField(max_length=500, blank=True)  # Store image path
    created_at = models.DateTimeField(auto_now_add=True)
    likes = models.IntegerField(default=0)
    liked_by = models.JSONField(default=list)  # Store usernames who liked the post
    
    class Meta:
        ordering = ['-created_at']  # Newest first
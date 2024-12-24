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
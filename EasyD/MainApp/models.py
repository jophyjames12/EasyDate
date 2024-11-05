from djongo import models
from django.conf import settings

class CustomUser(models.Model):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)  # Store hashed passwords
    created_at = models.DateTimeField(auto_now_add=True)

class FriendRequest(models.Model):
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='from_user', on_delete=models.CASCADE)
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='to_user', on_delete=models.CASCADE)
    is_accepted = models.BooleanField(default=False)

class FriendList(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    friends = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='friends', blank=True)
    
    def add_friend(self, friend):
        self.friends.add(friend)
        self.save()

    def remove_friend(self, friend):
        self.friends.remove(friend)
        self.save()
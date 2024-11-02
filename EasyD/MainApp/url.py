from django.contrib import admin
from django.urls import path
from MainApp import views

urlpatterns = [
    path("", views.login_view, name="home"),
    path("signup/", views.signup_view, name="signup")
    
]

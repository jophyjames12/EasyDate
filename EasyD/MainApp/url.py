from django.contrib import admin
from django.urls import path
from MainApp import views

urlpatterns=[
    path("",views.login_view, name="home"),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    #path("home/",views.home,name="home"),
]



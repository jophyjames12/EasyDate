from django.contrib import admin
from django.urls import path
from MainApp import views

urlpatterns=[
    path("",views.login_view, name="home"),
    path('login/', views.login_view, name='login'),
    path("area/",views.area_view, name='area' ),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('area/logout/', views.logout_view, name='logout'),
    path("home/",views.home,name="home"),
    path("search/", views.search_user, name='search_user'),
    path("send-request/<int:to_user_id>/", views.send_friend_request, name='send_friend_request'),
    path("accept-request/<int:friend_request_id>/", views.accept_friend_request, name='accept_friend_request'),
]


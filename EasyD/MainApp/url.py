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
    path("area/friendreq/", views.check_request, name='friendreq'),
    path("friendreq/", views.check_request, name='friendreq'),
    path("accept_request/",views.accept_request,name='accept_request'),
    path("reject_request/",views.reject_request,name='reject_request'),
    path("area/search_user/", views.search_user, name='search_user'),
    path("search_user/", views.search_user, name='search_user'),
]
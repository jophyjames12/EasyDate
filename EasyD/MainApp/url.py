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
    path('send_date_request/', views.send_date_request, name='send_date_request'),
    path("search_user/", views.search_user, name='search_user'),
    path('map/', views.map_view, name='map_view'),
    path('area/map/', views.map_view, name='map_view'),
    path("profile/", views.profile, name="profile"),  # Profile URL
    path('handle_date_request/', views.handle_date_request, name='handle_date_request'),
    path('profile/', views.profile_view, name='profile'),
    path('rate_place/', views.rate_place, name='rate_place'),
    #path('api/places/', views.get_places, name='get_places'),
    #path("sort_places_by_reviews/", views.sort_places_by_reviews, name="sort_places_by_reviews"),
    path('update-preferences/', views.update_preferences, name='update_preferences'),
    path('update_location/', views.update_location, name='update_location'),

]
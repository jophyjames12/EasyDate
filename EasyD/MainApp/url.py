from django.contrib import admin
from django.urls import path
from MainApp import views
from django.conf import settings
from django.conf.urls.static import static

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
    #path('rate_place/', views.rate_place, name='rate_place'),
    #path('api/places/', views.get_places, name='get_places'),
    #path("sort_places_by_reviews/", views.sort_places_by_reviews, name="sort_places_by_reviews"),
    path('update-preferences/', views.update_preferences, name='update_preferences'),
    path('update_location/', views.update_location, name='update_location'),
    path('date-map/<str:request_id>/', views.date_map_view, name='date_map'),
    path('get-route/', views.get_osrm_route, name='get_osrm_route'),
    path('edit_profile/', views.edit_profile, name='edit_profile'),
    path('get_preferred_places/', views.get_preferred_places, name='get_preferred_places'),
    path('get_reviews/', views.get_place_reviews, name='get_place_reviews'),
    path('old-dates/', views.old_dates_view, name='old_dates'),
    path('save_date_location/', views.save_date_location, name='save_date_location'),
    path('get_date_location/', views.get_date_location, name='get_date_location'),
    path('remove_date_location/', views.remove_date_location, name='remove_date_location'),
    path('get_upcoming_dates/', views.get_user_upcoming_dates, name='get_upcoming_dates'),
    path('select-date-location/<str:request_id>/', views.date_location_selection_view, name='select_date_location'),
    path('events/', views.events_view, name='events'),
    path('create_event/', views.create_event, name='create_event'),
    path('approve_event/', views.approve_event, name='approve_event'),
    path('reject_event/', views.reject_event, name='reject_event'),
    path('get_event_details/<str:event_id>/', views.get_event_details, name='get_event_details'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
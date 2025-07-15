from asyncio.log import logger
from tkinter import Place
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from bson.objectid import ObjectId
from pymongo import MongoClient
from passlib.hash import pbkdf2_sha256  # For password hashing
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
import requests
import os
import math 
import uuid
from datetime import datetime,date
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import logging
logger = logging.getLogger(__name__)

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['UserDetails']
users_collection = db['AccountHashing']
FriendReq = db['Friendrequest']
Friendlist = db['FriendList']
DateReq = db['DateRequests']  # New collection for date requests
OldDates = db['OldDates']  # New collection for old dates
Preference = db['PreferenceList']
Review=db['Reviews']
Location=db['Location']
Profiles = db['Profiles']  # New collection for storing profile info

@csrf_exempt
def get_place_reviews(request):
    """
    Fetch reviews for a place using Google Places API
    """
    if request.method == 'GET':
        try:
            # Get parameters from request
            place_name = request.GET.get('name', '')
            lat = request.GET.get('lat', '')
            lon = request.GET.get('lon', '')
            
            if not all([place_name, lat, lon]):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Missing required parameters: name, lat, lon'
                })
            
            # Check if API key is configured
            if not settings.GOOGLE_PLACES_API_KEY:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Google Places API key not configured'
                })
            
            # Step 1: Find the place using Places API Text Search
            search_url = 'https://maps.googleapis.com/maps/api/place/textsearch/json'
            search_params = {
                'query': f"{place_name}",
                'location': f"{lat},{lon}",
                'radius': 500,  # 500 meters radius
                'key': settings.GOOGLE_PLACES_API_KEY
            }
            
            search_response = requests.get(search_url, params=search_params)
            search_data = search_response.json()
            
            if search_data.get('status') != 'OK' or not search_data.get('results'):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Place not found in Google Places'
                })
            
            # Get the first result (most relevant)
            place = search_data['results'][0]
            place_id = place.get('place_id')
            
            if not place_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Place ID not found'
                })
            
            # Step 2: Get place details including reviews
            details_url = 'https://maps.googleapis.com/maps/api/place/details/json'
            details_params = {
                'place_id': place_id,
                'fields': 'name,rating,user_ratings_total,reviews,formatted_address,opening_hours,formatted_phone_number,website',
                'key': settings.GOOGLE_PLACES_API_KEY
            }
            
            details_response = requests.get(details_url, params=details_params)
            details_data = details_response.json()
            
            if details_data.get('status') != 'OK':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Failed to fetch place details'
                })
            
            place_details = details_data.get('result', {})
            
            # Extract relevant information
            reviews_data = {
                'status': 'success',
                'place_name': place_details.get('name', place_name),
                'rating': place_details.get('rating', 0),
                'total_ratings': place_details.get('user_ratings_total', 0),
                'address': place_details.get('formatted_address', ''),
                'phone': place_details.get('formatted_phone_number', ''),
                'website': place_details.get('website', ''),
                'opening_hours': place_details.get('opening_hours', {}).get('weekday_text', []),
                'reviews': []
            }
            
            # Process reviews
            reviews = place_details.get('reviews', [])
            for review in reviews[:5]:  # Limit to 5 reviews
                review_data = {
                    'author_name': review.get('author_name', 'Anonymous'),
                    'rating': review.get('rating', 0),
                    'text': review.get('text', ''),
                    'time': review.get('relative_time_description', ''),
                    'profile_photo_url': review.get('profile_photo_url', '')
                }
                reviews_data['reviews'].append(review_data)
            
            return JsonResponse(reviews_data)
            
        except requests.RequestException as e:
            return JsonResponse({
                'status': 'error',
                'message': f'API request failed: {str(e)}'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Server error: {str(e)}'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Only GET method allowed'
    })

@csrf_exempt
def update_location(request):
    userinfo(request)
    if request.method == 'POST':
        lat = None
        lon = None
        
        # Try to parse JSON first
        try:
            data = json.loads(request.body)
            lat = data.get('latitude')
            lon = data.get('longitude')
        except (json.JSONDecodeError, TypeError):
            # Fallback to form data
            lat = request.POST.get('latitude')
            lon = request.POST.get('longitude')

        # Debug logging
        print(f"DEBUG - Received coordinates: lat={lat}, lon={lon}")
        print(f"DEBUG - User: {name}")

        if lat is None or lon is None:
            print("DEBUG - Missing latitude or longitude")
            return JsonResponse({'status': 'error', 'message': 'Missing latitude or longitude'}, status=400)
        
        try:
            lat = float(lat)
            lon = float(lon)
            print(f"DEBUG - Converted to floats: lat={lat}, lon={lon}")
        except ValueError as e:
            print(f"DEBUG - Conversion error: {e}")
            return JsonResponse({'status': 'error', 'message': 'Invalid latitude or longitude'}, status=400)

        # Validate coordinate ranges
        if not (-90 <= lat <= 90):
            print(f"DEBUG - Invalid latitude range: {lat}")
            return JsonResponse({'status': 'error', 'message': 'Latitude must be between -90 and 90'}, status=400)
            
        if not (-180 <= lon <= 180):
            print(f"DEBUG - Invalid longitude range: {lon}")
            return JsonResponse({'status': 'error', 'message': 'Longitude must be between -180 and 180'}, status=400)

        # Check for null island (0,0) which is often a default value
        if lat == 0 and lon == 0:
            print("DEBUG - Warning: Coordinates are at 0,0 (Null Island)")
            return JsonResponse({'status': 'error', 'message': 'Invalid coordinates: 0,0 is not a valid location'}, status=400)

        try:
            existing = Location.find_one({'name': name})
            if existing:
                print(f"DEBUG - Updating existing location for {name}")
                result = Location.update_one(
                    {'_id': existing['_id']}, 
                    {'$set': {'lat': lat, 'lon': lon, 'updated_at': datetime.now()}}
                )
                print(f"DEBUG - Update result: {result.modified_count} modified")
            else:
                print(f"DEBUG - Creating new location for {name}")
                result = Location.insert_one({
                    'name': name, 
                    'lat': lat, 
                    'lon': lon, 
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                })
                print(f"DEBUG - Insert result: {result.inserted_id}")
            
            # Verify the save
            saved_location = Location.find_one({'name': name})
            print(f"DEBUG - Saved location: {saved_location}")
            
            return JsonResponse({
                'status': 'success', 
                'message': 'Location updated successfully',
                'coordinates': {'lat': lat, 'lon': lon}
            })
            
        except Exception as e:
            print(f"DEBUG - Database error: {e}")
            return JsonResponse({'status': 'error', 'message': f'Database error: {str(e)}'}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

# Retrieves user information from session and fetches username from database
def userinfo(request):
    global user
    user = request.session.get('user_id')
    global name
    # Fetch the username from MongoDB using the user ID in the session
    name = users_collection.find_one({"_id": ObjectId(user)}).get('username')

# Home view to check if user is logged in; if not, redirect to login
def home(request):
    if not request.session.get('user_id'):
        # If user is not logged in, show login page
        return render(request, 'MainApp/login.html')
    # If logged in, show the main area page
    return render(request, 'MainApp/area.html')

# Login view to handle user authentication
def login_view(request):
    # If user is already logged in, redirect to the main area page
    if request.session.get('user_id'):
        return render(request, 'MainApp/area.html')

    if request.method == 'POST':
        # Retrieve submitted username and password from form
        username = request.POST['username']
        password = request.POST['password']

        # Fetch the user record from MongoDB by username
        user = users_collection.find_one({"username": username})
        if user and pbkdf2_sha256.verify(password, user['password']):
            # If user exists and password is correct, create session and redirect
            request.session['user_id'] = str(user['_id'])
            request.session['login_success'] = True
            return redirect('area')
        else:
            # Display error if login details are invalid
            messages.error(request, "Invalid username or password")
    return render(request, 'MainApp/login.html')

# Signup view to handle user registration
def signup_view(request):
    # Redirects logged-in users to the main area page
    if request.session.get('user_id'):
        return redirect('area_view')

    if request.method == 'POST':
        # Retrieve form data for user registration
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        # Check if passwords match
        if password == confirm_password:
            # Check if username or email already exists in MongoDB
            if users_collection.find_one({"username": username}):
                messages.error(request, "Username already exists")
            elif users_collection.find_one({"email": email}):
                messages.error(request, "Email already registered")
            else:
                # Hash the password and save the new user in MongoDB
                hashed_password = pbkdf2_sha256.hash(password)
                new_user = {
                    "username": username,
                    "email": email,
                    "password": hashed_password
                }
                users_collection.insert_one(new_user)
                # Start session for the newly registered user
                request.session['user_id'] = str(new_user['_id'])
                request.session['account_created'] = True
                return redirect('area')
        else:
            # Display error if passwords do not match
            messages.error(request, "Passwords do not match")
    return render(request, 'MainApp/signup.html')

# Area view to display main content for logged-in users
def area_view(request):
    if not request.session.get('user_id'):
        return redirect('login')
    # Get user info
    userinfo(request)
    # Move old dates to separate collection
    move_old_dates()
    # Retrieve session flags for success messages
    account_created = request.session.get('account_created', False)
    login_success = request.session.get('login_success', False)
    
    # Clear session flags after displaying
    if 'account_created' in request.session:
        del request.session['account_created']
    if 'login_success' in request.session:
        del request.session['login_success']
    
    # Fetch upcoming accepted dates for the current user
    upcoming_dates = list(DateReq.find({
        "$or": [
            {"From": name, "status": "accepted"},
            {"To": name, "status": "accepted"}
        ]
    }))
    # Fetch old dates for the current user (last 10 for reference)
    old_dates = list(OldDates.find({
        "$or": [
            {"From": name, "status": "accepted"},
            {"To": name, "status": "accepted"}
        ]
    }).sort("moved_at", -1).limit(10))

    # Process upcoming dates to get partner info
    processed_upcoming_dates = []
    for date_req in upcoming_dates:
        partner = date_req["To"] if date_req["From"] == name else date_req["From"]
        processed_upcoming_dates.append({
            'date': date_req.get('date', ''),
            'time': date_req.get('time', ''),
            'partner': partner,
            'request_id': str(date_req['_id']),
            'status': 'upcoming'
        })
    
    # Process old dates to get partner info
    processed_old_dates = []
    for date_req in old_dates:
        partner = date_req["To"] if date_req["From"] == name else date_req["From"]
        processed_old_dates.append({
            'date': date_req.get('date', ''),
            'time': date_req.get('time', ''),
            'partner': partner,
            'request_id': str(date_req.get('original_id', date_req['_id'])),
            'status': 'past'
        })
    # Sort upcoming dates by date
    processed_upcoming_dates.sort(key=lambda x: x['date'] if x['date'] else '')
    # Pass success messages and dates to the template
    return render(request, 'MainApp/area.html', {
        'account_created': account_created, 
        'login_success': login_success,
        'upcoming_dates': processed_upcoming_dates,
        'old_dates': processed_old_dates,
        'accepted_dates': processed_upcoming_dates  # Keep for backward compatibility
    })

def logout_view(request):
    if 'user_id' in request.session:
        # Remove user ID from session to log the user out
        del request.session['user_id']
    # Clear messages properly after the user logs out
    messages.get_messages(request).used = True  # This clears all messages
    return redirect('login')

# View to handle user search and friend request functionality
def search_user(request):
    userinfo(request)  # Retrieve logged-in user's info
    if request.method == "POST":
        # Get the username input from the search form
        username = request.POST.get('username')
        lat = request.POST.get('latitude')
        lon = request.POST.get('longitude')

        # Assuming you are searching for the user by some unique identifier (like 'name')

            # Fetch user location based on the name (or another identifier like 'friendname')
        usename = Location.find_one({'name': name})  # Make sure the correct field is used for lookup
        if not usename:
            Location.insert_one({'name':name,'lat':lat,'lon':lon})
        # Check if the user was found, if so, update the latitude and longitude
        if usename:
            usename['lat'] = lat
            usename['lon'] = lon
            # Update the user's location in the database (instead of inserting)
            Location.update_one({'_id': usename['_id']}, {'$set': {'lat': lat, 'lon': lon}})
        if not username:
            # Display error if username is not provided
            messages.error(request, "No username provided.")
            return redirect("search_user")
        
        # Find the target user in MongoDB by username
        target_user = users_collection.find_one({"username": username})
        
        if target_user:
            if username == name:
                # Prevent user from sending a friend request to themselves
                messages.error(request, "You cannot send a friend request to yourself.")
                return redirect("search_user")
            
            # Check if a friend request already exists
            existing_request = FriendReq.find_one({"From": name, "To": username}) or FriendReq.find_one({"From": username, "To": name})
            user_friendlist = Friendlist.find_one({"username": name})
            
            if user_friendlist and username in user_friendlist.get("friends", []):
                # Notify if the user is already in the friend list
                messages.info(request, "This user is already in your friend list.")
                return redirect("search_user")
            
            if existing_request:
                # Notify if a friend request has already been sent
                messages.info(request, "Friend request already sent. Waiting for response.")
                return redirect("search_user")
            
            # Send a new friend request by adding it to the database
            friend_request = {
                "From": name,
                "To": username
            }
            FriendReq.insert_one(friend_request)
            messages.success(request, f"Friend request sent to {username}.")
            return redirect("search_user")
        
        # Display error if the target user is not found
        messages.error(request, "User not found.")
        return redirect("search_user")
    
    # Retrieve pending friend requests and list of all friends for the logged-in user
    friends = []
    friend_requests = FriendReq.find({"To": name})
    for friend in friend_requests:
        # Append each friend request sender to the friends list
        friends.append(friend["From"])

    # Retrieve the logged-in user's friends list
    user_friendlist = Friendlist.find_one({"username": name})
    all_friends = user_friendlist.get("friends", []) if user_friendlist else []

    # Render the search page with friend requests and friends list
    return render(request, "MainApp/search.html", {"friends": friends, "all_friends": all_friends})

# Check and display pending friend requests for the user
def check_request(request):
    userinfo(request)
    # Find friend requests sent to the logged-in user
    pending_requests = FriendReq.find({"To": name})
    friends = []
    for friend_request in pending_requests:
        # Add each pending request sender to the friends list
        friends.append(friend_request["From"])
    # Display pending requests on the search page
    return render(request, "MainApp/search.html", {"friends": friends})

# Accept friend request by updating friend lists
def accept_request(request):
    userinfo(request)

    if request.method == "POST":
        lat = request.POST.get('latitude')
        lon = request.POST.get('longitude')

        # Assuming you are searching for the user by some unique identifier (like 'name')

            # Fetch user location based on the name (or another identifier like 'friendname')
        usename = Location.find_one({'name': name})  # Make sure the correct field is used for lookup
        if not usename:
            Location.insert_one({'name':name,'lat':lat,'lon':lon})
        # Check if the user was found, if so, update the latitude and longitude
        if usename:
            usename['lat'] = lat
            usename['lon'] = lon
            # Update the user's location in the database (instead of inserting)
            Location.update_one({'_id': usename['_id']}, {'$set': {'lat': lat, 'lon': lon}})
        # Get the sender's username from the form data
        friendname = request.POST.get('friend_id')
        friend_request = FriendReq.find_one({"From": friendname, "To": name})
        if friend_request:
            sender = friend_request["From"]
            receiver = name
            # Add receiver to sender's friend list and vice versa
            Friendlist.update_one(
                {"username": sender},
                {"$addToSet": {"friends": receiver}},
                upsert=True
            )
            Friendlist.update_one(
                {"username": receiver},
                {"$addToSet": {"friends": sender}},
                upsert=True
            )
            
            FriendReq.delete_one({"From": friendname, "To": name}) # Delete the accepted friend request
            messages.success(request, f"You are now friends with {friendname}.")
    return redirect("search_user")

def reject_request(request): # Reject friend request by removing it from the database
    if request.method == "POST":
        # Get the sender's username from the form data
        friendname = request.POST.get('friend_id')
        # Delete the friend request from the database
        FriendReq.delete_one({"From": friendname, "To": name})
        messages.success(request, f"Friend request from {friendname} rejected!")
    return redirect("search_user")

def send_date_request(request):
    userinfo(request)
    if request.method == "POST":
        friendname = request.POST.get('friend_id')

        # Assuming you are searching for the user by some unique identifier (like 'name')
        try:
            # Fetch user location based on the name (or another identifier like 'friendname')
            usename = Location.find_one({'name': name})  # Make sure the correct field is used for lookup
        except:
            print("Error while fetching user location")
            return redirect('search_user')  # Handle case if the user is not found


        date = request.POST.get('date')
        time = request.POST.get('time')

        # Ensure the user isn't trying to send a date request to themselves
        if friendname == name:
            messages.error(request, "You cannot send a date request to yourself.")
            return redirect('search_user')

        # Check if the friend is in the user's friend list
        user_friendlist = Friendlist.find_one({"username": name})
        if not user_friendlist or friendname not in user_friendlist.get("friends", []):
            messages.error(request, "You can only send a date request to your friends.")
            return redirect('search_user')

        # Check for an existing date request
        existing_date_request = DateReq.find_one({"From": name, "To": friendname}) or DateReq.find_one({"From": friendname, "To": name})

        if existing_date_request:
            messages.info(request, "Date request already sent. Waiting for response.")
            return redirect("search_user")

        # Create a new date request with date and time (date_location starts as null)
        date_request = {
            "From": name,
            "To": friendname,
            "status": "pending",
            "date": date,
            "time": time,
            "date_location": None  # Initially null, can be set later by sender
        }
        DateReq.insert_one(date_request)
        messages.success(request, f"Date request sent to {friendname}.")
        return redirect("search_user")

def profile(request):
    userinfo(request)
    # Fetch user profile information
    user_profile = Profiles.find_one({"username": name})
    bio = user_profile.get("bio", "Welcome to my profile! Let's connect and have some fun together.") if user_profile else "Welcome to my profile! Let's connect and have some fun together."
    profile_picture = user_profile.get("profile_picture", None) if user_profile else None
    # Fetch the pending date requests for the user
    sent_requests = DateReq.find({"From": name, "status": "pending"})
    received_requests = DateReq.find({"To": name, "status": "pending"})
    
    # Fetch accepted dates (upcoming dates)
    upcoming_dates = DateReq.find({
        "$or": [
            {"From": name, "status": "accepted"},
            {"To": name, "status": "accepted"}
        ]
    })
    
    # Get the user's friend count
    user_friendlist = Friendlist.find_one({"username": name})
    friend_count = len(user_friendlist.get("friends", [])) if user_friendlist else 0
    
    # Prepare lists with location info
    sent_from = []
    for req in sent_requests:
        req_data = {
            "username": req["To"], 
            "request_id": str(req["_id"]),
            "date": req.get("date", ""),
            "time": req.get("time", ""),
            "date_location": req.get("date_location", None),
            "can_set_location": True  # Sender can always set location
        }
        sent_from.append(req_data)
    
    received_from = []
    for req in received_requests:
        req_data = {
            "username": req["From"],
            "request_id": str(req["_id"]),
            "date": req.get("date", ""),
            "time": req.get("time", ""),
            "date_location": req.get("date_location", None),
            "can_set_location": False  # Receiver cannot set location
        }
        received_from.append(req_data)
    
    # Process upcoming dates
    upcoming_dates_list = []
    for req in upcoming_dates:
        partner = req["To"] if req["From"] == name else req["From"]
        is_sender = req["From"] == name
        
        date_data = {
            "partner": partner,
            "request_id": str(req["_id"]),
            "date": req.get("date", ""),
            "time": req.get("time", ""),
            "date_location": req.get("date_location", None),
            "can_set_location": is_sender,
            "is_sender": is_sender
        }
        upcoming_dates_list.append(date_data)
    
    return render(request, 'MainApp/profile.html', {
        "sent_from": sent_from,
        "received_from": received_from,
        "upcoming_dates": upcoming_dates_list,
        "name": name,
        "friend_count": friend_count,
        "post_count": 0,
        "bio": bio,
        "profile_picture": profile_picture
    })

# Edit profile view
def edit_profile(request):
    if not request.session.get('user_id'):
        return redirect('login')
    
    # Get user info first
    userinfo(request)
    
    # Get current user data from session/global variables
    user_id = request.session.get('user_id')
    # Assuming 'name' and 'user' are set by userinfo() function
    # If not, you need to get them from the database or session
    
    if request.method == 'POST':
        try:
            # Get the bio from the form
            bio = request.POST.get('bio', '').strip()
            
            # Handle profile picture upload
            profile_picture = request.FILES.get('profile_picture')
            profile_picture_url = None
            old_profile_picture = None
            
            # Get existing profile to check for old picture
            existing_profile = Profiles.find_one({"username": name})
            if existing_profile:
                old_profile_picture = existing_profile.get("profile_picture")
            
            if profile_picture:
                # Validate file size (5MB limit)
                if profile_picture.size > 5 * 1024 * 1024:
                    messages.error(request, "Profile picture must be less than 5MB.")
                    return redirect('edit_profile')
                
                # Validate file type
                allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
                if profile_picture.content_type not in allowed_types:
                    messages.error(request, "Please upload a valid image file (JPG, PNG, GIF).")
                    return redirect('edit_profile')
                
                # Create uploads directory if it doesn't exist
                upload_dir = os.path.join(settings.MEDIA_ROOT, 'profile_pictures')
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir, mode=0o755)
                
                # Generate unique filename with timestamp to avoid conflicts
                file_extension = os.path.splitext(profile_picture.name)[1].lower()
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                unique_id = str(uuid.uuid4())[:8]
                filename = f"{name}_{timestamp}_{unique_id}{file_extension}"
                file_path = os.path.join(upload_dir, filename)
                
                # Delete old profile picture if it exists
                if old_profile_picture:
                    old_file_path = os.path.join(settings.MEDIA_ROOT, old_profile_picture.lstrip('/media/'))
                    if os.path.exists(old_file_path):
                        try:
                            os.remove(old_file_path)
                        except OSError:
                            pass  # Continue if file can't be deleted
                
                # Save the new file
                try:
                    with open(file_path, 'wb+') as destination:
                        for chunk in profile_picture.chunks():
                            destination.write(chunk)
                    
                    # Verify file was saved successfully
                    if not os.path.exists(file_path):
                        messages.error(request, "Failed to save profile picture. Please try again.")
                        return redirect('edit_profile')
                    
                    # Store relative path for database
                    profile_picture_url = f"/media/profile_pictures/{filename}"
                    
                except Exception as e:
                    messages.error(request, f"Error saving profile picture: {str(e)}")
                    return redirect('edit_profile')
            
            # Update or create profile in database
            try:
                if existing_profile:
                    # Update existing profile
                    update_data = {
                        "bio": bio,
                        "updated_at": datetime.now()
                    }
                    if profile_picture_url:
                        update_data["profile_picture"] = profile_picture_url
                    
                    result = Profiles.update_one(
                        {"username": name},
                        {"$set": update_data}
                    )
                    
                    if result.modified_count == 0 and result.matched_count == 0:
                        messages.error(request, "Failed to update profile. Please try again.")
                        return redirect('edit_profile')
                        
                else:
                    # Create new profile
                    profile_data = {
                        "username": name,
                        "bio": bio,
                        "created_at": datetime.now(),
                        "updated_at": datetime.now()
                    }
                    if profile_picture_url:
                        profile_data["profile_picture"] = profile_picture_url
                    
                    result = Profiles.insert_one(profile_data)
                    
                    if not result.inserted_id:
                        messages.error(request, "Failed to create profile. Please try again.")
                        return redirect('edit_profile')
                
                messages.success(request, "Profile updated successfully!")
                return redirect('profile')
                
            except Exception as e:
                messages.error(request, f"Database error: {str(e)}")
                return redirect('edit_profile')
                
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('edit_profile')
    
    # GET request - show edit form
    try:
        user_profile = Profiles.find_one({"username": name})
        bio = user_profile.get("bio", "Welcome to my profile! Let's connect and have some fun together.") if user_profile else "Welcome to my profile! Let's connect and have some fun together."
        profile_picture = user_profile.get("profile_picture", None) if user_profile else None
        
        return render(request, 'MainApp/edit_profile.html', {
            "name": name,
            "bio": bio,
            "profile_picture": profile_picture
        })
        
    except Exception as e:
        messages.error(request, f"Error loading profile: {str(e)}")
        return redirect('profile')

# Handle accepting or rejecting a date request
def handle_date_request(request):
    userinfo(request)

    if request.method == "POST":
        request_id = request.POST.get('request_id')
        action = request.POST.get('action')  # either 'accept' or 'reject'

        # Fetch the date request
        date_request = DateReq.find_one({"_id": ObjectId(request_id)})

        if date_request:
            if action == "accept":
                # Get the current date/time from the request
                current_date = date_request.get("date", "")
                current_time = date_request.get("time", "")
                
                # Option to change the date or time before accepting
                new_date = request.POST.get('new_date')
                new_time = request.POST.get('new_time')
                
                # Debug logging
                print(f"DEBUG - Current date: '{current_date}', Current time: '{current_time}'")
                print(f"DEBUG - New date: '{new_date}', New time: '{new_time}'")
                
                # Use new values if provided, otherwise keep existing (but validate they're not empty)
                final_date = new_date if new_date and new_date.strip() else current_date
                final_time = new_time if new_time and new_time.strip() else current_time
                
                # If we still don't have date/time, require them
                if not final_date or not final_time or final_date.strip() == "" or final_time.strip() == "":
                    messages.error(request, "Date and time are required to accept the date request. Please provide both.")
                    return redirect('profile')
                
                # Clean up the values
                final_date = final_date.strip()
                final_time = final_time.strip()
                
                # Debug logging
                print(f"DEBUG - Final date: '{final_date}', Final time: '{final_time}'")
                
                # Update the date request with the new date/time (preserve existing date_location)
                update_result = DateReq.update_one({"_id": ObjectId(request_id)}, {
                    "$set": {
                        "status": "accepted", 
                        "date": final_date, 
                        "time": final_time
                    }
                })
                
                # Debug logging
                print(f"DEBUG - Update result: {update_result.modified_count} documents modified")
                
                # Verify the update
                updated_request = DateReq.find_one({"_id": ObjectId(request_id)})
                print(f"DEBUG - Updated document: {updated_request}")
                
                if new_date or new_time:
                    messages.success(request, f"Date request accepted with updated details: {final_date} at {final_time}.")
                else:
                    messages.success(request, f"Date request accepted for {final_date} at {final_time}.")
                    
            elif action == "reject":
                DateReq.delete_one({"_id": ObjectId(request_id)})
                messages.success(request, "Date request rejected.")
        else:
            messages.error(request, "Date request not found.")

    return redirect('profile')

def map_view(request):
    return render(request,'MainApp/Map.html')

@csrf_exempt
def update_preferences(request):
    userinfo(request)
    if request.method == 'POST':
        selected_preferences = request.POST.get('selected_preferences', '')
        # Convert the comma-separated string into a list
        preferences = selected_preferences.split(',')
        # Find the user in the database or create a new record
        existing_user = Preference.find_one({'name': name})
        
        if existing_user:
            # Update preferences if user already has a document
            Preference.update_one({"name": name}, {"$set": {"preferences": preferences}})
        else:
            # Insert new document if user doesn't have one
            Preference.insert_one({"name": name, "preferences": preferences})
        
        return redirect("area")
    else:
        return JsonResponse({"status": "error", "message": "Invalid request method."})

@csrf_exempt
def get_places(request):
    places = list(places.objects.all().values())
    return JsonResponse(places, safe=False)
      #  return JsonResponse({"message": "Preferences saved successfully"})
   # return JsonResponse({"error": "Invalid request"}, status=400)

def get_combined_preferences(user1_name, user2_name):
    """Get combined preferences for both users"""
    user1_prefs = Preference.find_one({'name': user1_name})
    user2_prefs = Preference.find_one({'name': user2_name})
    
    # Get preferences lists, default to empty if not found
    user1_list = user1_prefs.get('preferences', []) if user1_prefs else []
    user2_list = user2_prefs.get('preferences', []) if user2_prefs else []
    
    # Find common preferences (intersection)
    common_prefs = list(set(user1_list) & set(user2_list))
    
    # If no common preferences, include all preferences from both users
    if not common_prefs:
        all_prefs = list(set(user1_list + user2_list))
        return all_prefs
    
    return common_prefs

# Also add debugging to your get_preferred_places view
@csrf_exempt
def get_preferred_places(request):
    """Get places filtered by user preferences for date mode - with debugging"""
    if not request.session.get('user_id'):
        return JsonResponse({'status': 'error', 'message': 'Not authenticated'}, status=401)
    
    userinfo(request)
    
    # Get parameters
    try:
        lat = float(request.GET.get('lat', 0))
        lon = float(request.GET.get('lon', 0))
        partner_name = request.GET.get('partner', '')
        
        logger.info(f"Getting preferred places for {name} and {partner_name} at {lat}, {lon}")
        
        if not lat or not lon or not partner_name:
            logger.error(f"Missing parameters: lat={lat}, lon={lon}, partner={partner_name}")
            return JsonResponse({'status': 'error', 'message': 'Missing required parameters'}, status=400)
        
        # Get combined preferences for both users
        preferred_tags = get_combined_preferences(name, partner_name)
        logger.info(f"Combined preferences: {preferred_tags}")
        
        # If no preferences found, default to all available options
        if not preferred_tags:
            preferred_tags = ['restaurant', 'cafe', 'bar', 'club', 'shop']
            logger.info("No preferences found, using default tags")
        
        # Map preferences to amenity tags
        preference_to_amenity = {
            'restaurant': 'restaurant',
            'cafe': 'cafe', 
            'bar': 'bar',
            'club': 'club',
            'shop': 'shop'
        }
        
        # Convert preferences to amenity tags
        amenity_tags = []
        for pref in preferred_tags:
            if pref in preference_to_amenity:
                amenity_tags.append(preference_to_amenity[pref])
        
        logger.info(f"Amenity tags to search: {amenity_tags}")
        
        # If no valid amenity tags, default to restaurant
        if not amenity_tags:
            amenity_tags = ['restaurant']
            logger.warning("No valid amenity tags, defaulting to restaurant")
        
        # Fetch places for each preferred amenity type
        all_places = []
        for tag in amenity_tags:
            logger.info(f"Fetching places for tag: {tag}")
            places = fetch_overpass_places(lat, lon, tag)
            logger.info(f"Found {len(places)} places for {tag}")
            all_places.extend(places)
        
        logger.info(f"Total places found: {len(all_places)}")
        
        # Remove duplicates based on coordinates
        seen_coords = set()
        unique_places = []
        for place in all_places:
            place_lat = place.get('lat') or (place.get('center', {}).get('lat'))
            place_lon = place.get('lon') or (place.get('center', {}).get('lon'))
            
            if place_lat and place_lon:
                coord_key = f"{place_lat:.6f},{place_lon:.6f}"
                if coord_key not in seen_coords:
                    seen_coords.add(coord_key)
                    unique_places.append(place)
        
        logger.info(f"Unique places after deduplication: {len(unique_places)}")
        
        return JsonResponse({
            'status': 'success',
            'places': unique_places,
            'preferred_tags': preferred_tags,
            'debug': {
                'total_found': len(all_places),
                'unique_found': len(unique_places),
                'searched_tags': amenity_tags
            }
        })
        
    except ValueError as e:
        logger.error(f"Value error: {e}")
        return JsonResponse({'status': 'error', 'message': 'Invalid parameters'}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return JsonResponse({'status': 'error', 'message': 'Internal server error'}, status=500)

def fetch_overpass_places(lat, lon, amenity_type, radius=2000):
    """Fetch places from Overpass API with enhanced debugging"""
    
    # Add coordinate validation
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        logger.error(f"Invalid coordinates: lat={lat}, lon={lon}")
        return []
    
    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"="{amenity_type}"](around:{radius},{lat},{lon});
      way["amenity"="{amenity_type}"](around:{radius},{lat},{lon});
      relation["amenity"="{amenity_type}"](around:{radius},{lat},{lon});
    );
    out center;
    """
    url = 'https://overpass-api.de/api/interpreter'
    try:
        logger.info(f"Querying Overpass API for {amenity_type} at {lat}, {lon}")
        logger.debug(f"Query: {query}")
        response = requests.post(url, data={'data': query}, timeout=30)
        response.raise_for_status()
        data = response.json()
        elements = data.get('elements', [])
        logger.info(f"Found {len(elements)} places for {amenity_type}")
        # Log first few results for debugging
        for i, element in enumerate(elements[:3]):
            logger.debug(f"Place {i+1}: {element.get('tags', {}).get('name', 'Unnamed')} at {element.get('lat', 'N/A')}, {element.get('lon', 'N/A')}")
        return elements
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error fetching places for {amenity_type}: {e}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error for {amenity_type}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching places for {amenity_type}: {e}")
        return []

# Profile view to show user preferences
def profile_view(request):
    user = request.user
    preferences = user.preferences.all()  # Assuming the `preferences` field is a Many-to-Many relation
    return render(request, 'profile.html', {'user': user, 'preferences': preferences})

def date_map_view(request, request_id):
    if not request.session.get('user_id'):
        return redirect('login')
    userinfo(request)
    
    # Fetch the specific date request
    date_request = DateReq.find_one({"_id": ObjectId(request_id)})
    if not date_request:
        messages.error(request, "Date not found.")
        return redirect('area')
    
    # Get partner info
    partner = date_request["To"] if date_request["From"] == name else date_request["From"]
    
    # Get both users' locations with detailed error checking
    user_location = Location.find_one({'name': name})
    partner_location = Location.find_one({'name': partner})
    
    # Debug logging
    print(f"DEBUG - Current user: {name}")
    print(f"DEBUG - Partner: {partner}")
    print(f"DEBUG - User location data: {user_location}")
    print(f"DEBUG - Partner location data: {partner_location}")
    
    # Validate user location
    if not user_location:
        messages.error(request, f"Your location is not set. Please update your location in your profile.")
        return redirect('profile')
    
    if not user_location.get('lat') or not user_location.get('lon'):
        messages.error(request, f"Your location coordinates are incomplete. Please update your location.")
        return redirect('profile')
    
    # Validate partner location  
    if not partner_location:
        messages.error(request, f"{partner}'s location is not set. They need to update their location.")
        return redirect('profile')
    
    if not partner_location.get('lat') or not partner_location.get('lon'):
        messages.error(request, f"{partner}'s location coordinates are incomplete.")
        return redirect('profile')
    
    # Convert coordinates to float with error handling
    try:
        user_lat = float(user_location['lat'])
        user_lon = float(user_location['lon'])
        partner_lat = float(partner_location['lat'])
        partner_lon = float(partner_location['lon'])
        
        # Validate coordinate ranges
        if not (-90 <= user_lat <= 90) or not (-180 <= user_lon <= 180):
            messages.error(request, "Your location coordinates are invalid.")
            return redirect('profile')
            
        if not (-90 <= partner_lat <= 90) or not (-180 <= partner_lon <= 180):
            messages.error(request, f"{partner}'s location coordinates are invalid.")
            return redirect('profile')
            
    except (ValueError, TypeError) as e:
        messages.error(request, "Location coordinates are not in valid format.")
        print(f"DEBUG - Coordinate conversion error: {e}")
        return redirect('profile')
    
    # Debug - log final coordinates
    print(f"DEBUG - Final coordinates:")
    print(f"  User: {user_lat}, {user_lon}")
    print(f"  Partner: {partner_lat}, {partner_lon}")
    
    # Get combined preferences for context
    preferred_tags = get_combined_preferences(name, partner)
    
    # Prepare date info with validated coordinates
    date_info_dict = {
        'date': date_request.get('date', ''),
        'time': date_request.get('time', ''),
        'partner': partner,
        'user_lat': user_lat,
        'user_lon': user_lon,
        'partner_lat': partner_lat,
        'partner_lon': partner_lon,
        'preferred_tags': preferred_tags,
    }
    
    # Debug - log the final data being sent to template
    print(f"DEBUG - Date info being sent to template: {date_info_dict}")
    
    context = {
        'date_info': date_info_dict,
        'date_info_json': json.dumps(date_info_dict),
    }
    
    return render(request, 'MainApp/Map.html', context)

def get_osrm_route(request):
    # Example values — in real case, use session data or MongoDB query
    user_lat = float(request.GET.get("user_lat"))
    user_lon = float(request.GET.get("user_lon"))
    partner_lat = float(request.GET.get("partner_lat"))
    partner_lon = float(request.GET.get("partner_lon"))

    url = f"http://router.project-osrm.org/route/v1/driving/{user_lon},{user_lat};{partner_lon},{partner_lat}?overview=full&geometries=geojson"
    try:
        response = requests.get(url)
        data = response.json()
        geometry = data['routes'][0]['geometry']
        return JsonResponse(geometry)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
def move_old_dates():
    """Move dates that have passed their due date to OldDates collection"""
    try:
        today = date.today()
        old_dates = DateReq.find({  # Find all accepted dates that have passed
            "status": "accepted",
            "date": {"$exists": True, "$ne": ""}
        })
        moved_count = 0
        for date_req in old_dates:
            try:
                # Parse the date string (assuming format YYYY-MM-DD)
                date_str = date_req.get('date', '')
                if date_str:
                    # Handle different date formats
                    try:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError:
                        try:
                            date_obj = datetime.strptime(date_str, '%m/%d/%Y').date()
                        except ValueError:
                            try:
                                date_obj = datetime.strptime(date_str, '%d/%m/%Y').date()
                            except ValueError:
                                continue  # Skip if date format is not recognized
                    
                    # Check if date has passed
                    if date_obj < today:
                        # Add to OldDates collection
                        old_date_doc = dict(date_req)
                        old_date_doc['moved_at'] = datetime.now()
                        old_date_doc['original_id'] = date_req['_id']
                        # Insert into OldDates
                        OldDates.insert_one(old_date_doc)
                        # Remove from DateReq
                        DateReq.delete_one({"_id": date_req['_id']})
                        moved_count += 1
                        
            except Exception as e:
                logger.error(f"Error processing date {date_req.get('_id')}: {e}")
                continue
        
        logger.info(f"Moved {moved_count} old dates to OldDates collection")
        return moved_count
        
    except Exception as e:
        logger.error(f"Error in move_old_dates: {e}")
        return 0
    
def old_dates_view(request):
    """View to display all old dates for the user"""
    if not request.session.get('user_id'):
        return redirect('login')
    
    userinfo(request)
    # Fetch all old dates for the current user
    old_dates = list(OldDates.find({
        "$or": [
            {"From": name, "status": "accepted"},
            {"To": name, "status": "accepted"}
        ]
    }).sort("moved_at", -1))
    
    # Process old dates to get partner info
    processed_old_dates = []
    for date_req in old_dates:
        partner = date_req["To"] if date_req["From"] == name else date_req["From"]
        processed_old_dates.append({
            'date': date_req.get('date', ''),
            'time': date_req.get('time', ''),
            'partner': partner,
            'request_id': str(date_req.get('original_id', date_req['_id'])),
            'moved_at': date_req.get('moved_at', ''),
            'status': 'past'
        })
    return render(request, 'MainApp/old_dates.html', {
        'old_dates': processed_old_dates,
        'name': name
    })

# NEW FUNCTIONS FOR DATE LOCATION FEATURE

@csrf_exempt
def save_date_location(request):
    """
    Save selected location for a date request
    """
    if not request.session.get('user_id'):
        return JsonResponse({'status': 'error', 'message': 'Not authenticated'}, status=401)
    
    userinfo(request)
    
    if request.method == 'POST':
        try:
            # Get data from request
            data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
            
            request_id = data.get('request_id')
            place_name = data.get('place_name')
            place_lat = data.get('place_lat')
            place_lon = data.get('place_lon')
            place_address = data.get('place_address', '')
            place_type = data.get('place_type', '')
            
            # Validate required fields
            if not all([request_id, place_name, place_lat, place_lon]):
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Missing required fields: request_id, place_name, place_lat, place_lon'
                }, status=400)
            
            # Convert coordinates to float
            try:
                place_lat = float(place_lat)
                place_lon = float(place_lon)
            except ValueError:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Invalid coordinates'
                }, status=400)
            
            # Find the date request
            date_request = DateReq.find_one({"_id": ObjectId(request_id)})
            if not date_request:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Date request not found'
                }, status=404)
            
            # Check if user is the sender of the date request
            if date_request.get('From') != name:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Only the sender can set the date location'
                }, status=403)
            
            # Prepare location data
            location_data = {
                'name': place_name,
                'lat': place_lat,
                'lon': place_lon,
                'address': place_address,
                'type': place_type,
                'selected_by': name,
                'selected_at': datetime.now()
            }
            
            # Update the date request with location
            result = DateReq.update_one(
                {"_id": ObjectId(request_id)},
                {"$set": {"date_location": location_data}}
            )
            
            if result.modified_count > 0:
                return JsonResponse({
                    'status': 'success',
                    'message': f'Date location set to {place_name}',
                    'location': location_data
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Failed to update date location'
                }, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error saving date location: {e}")
            return JsonResponse({
                'status': 'error',
                'message': 'Internal server error'
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Only POST method allowed'
    }, status=405)


def get_user_upcoming_dates(request):
    """
    Get upcoming dates for the current user (both sent and received)
    """
    if not request.session.get('user_id'):
        return JsonResponse({'status': 'error', 'message': 'Not authenticated'}, status=401)
    
    userinfo(request)
    
    try:
        # Get all upcoming dates where user is involved
        upcoming_dates = list(DateReq.find({
            "$or": [
                {"From": name, "status": "accepted"},
                {"To": name, "status": "accepted"},
                {"From": name, "status": "pending"}  # Include pending requests sent by user
            ]
        }))
        
        processed_dates = []
        for date_req in upcoming_dates:
            partner = date_req["To"] if date_req["From"] == name else date_req["From"]
            is_sender = date_req["From"] == name
            
            date_info = {
                'request_id': str(date_req['_id']),
                'date': date_req.get('date', ''),
                'time': date_req.get('time', ''),
                'partner': partner,
                'status': date_req.get('status', ''),
                'is_sender': is_sender,
                'can_set_location': is_sender,  # Only sender can set location
                'date_location': date_req.get('date_location', None)
            }
            processed_dates.append(date_info)
        
        return JsonResponse({
            'status': 'success',
            'dates': processed_dates
        })
        
    except Exception as e:
        logger.error(f"Error getting upcoming dates: {e}")
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to fetch upcoming dates'
        }, status=500)


def date_location_selection_view(request, request_id):
    """
    View for selecting date location - enhanced map view
    """
    if not request.session.get('user_id'):
        return redirect('login')
    
    userinfo(request)
    
    # Fetch the specific date request
    date_request = DateReq.find_one({"_id": ObjectId(request_id)})
    if not date_request:
        messages.error(request, "Date request not found.")
        return redirect('area')
    
    # Check if user is the sender
    if date_request.get('From') != name:
        messages.error(request, "Only the sender can select the date location.")
        return redirect('area')
    
    # Get partner info
    partner = date_request["To"]
    
    # Get both users' locations
    user_location = Location.find_one({'name': name})
    partner_location = Location.find_one({'name': partner})
    
    # Get combined preferences for context
    preferred_tags = get_combined_preferences(name, partner)
    
    # Prepare date info with location selection mode
    date_info_dict = {
        'request_id': str(date_request['_id']),
        'date': date_request.get('date', ''),
        'time': date_request.get('time', ''),
        'partner': partner,
        'status': date_request.get('status', ''),
        'user_lat': float(user_location['lat']) if user_location else None,
        'user_lon': float(user_location['lon']) if user_location else None,
        'partner_lat': float(partner_location['lat']) if partner_location else None,
        'partner_lon': float(partner_location['lon']) if partner_location else None,
        'preferred_tags': preferred_tags,
        'mode': 'location_selection',  # Special mode for location selection
        'current_location': date_request.get('date_location', None)
    }
    
    context = {
        'date_info': date_info_dict,
        'date_info_json': json.dumps(date_info_dict),
        'location_selection_mode': True
    }
    
    return render(request, 'MainApp/Map.html', context)


@csrf_exempt
def get_date_location(request):
    """
    Get the current date location for a specific date request
    """
    if not request.session.get('user_id'):
        return JsonResponse({'status': 'error', 'message': 'Not authenticated'}, status=401)
    
    userinfo(request)
    
    try:
        request_id = request.GET.get('request_id')
        if not request_id:
            return JsonResponse({
                'status': 'error',
                'message': 'Missing request_id parameter'
            }, status=400)
        
        # Find the date request
        date_request = DateReq.find_one({"_id": ObjectId(request_id)})
        if not date_request:
            return JsonResponse({
                'status': 'error',
                'message': 'Date request not found'
            }, status=404)
        
        # Check if user is involved in this date
        if date_request.get('From') != name and date_request.get('To') != name:
            return JsonResponse({
                'status': 'error',
                'message': 'Access denied'
            }, status=403)
        
        date_location = date_request.get('date_location', None)
        
        return JsonResponse({
            'status': 'success',
            'date_location': date_location,
            'can_modify': date_request.get('From') == name  # Only sender can modify
        })
        
    except Exception as e:
        logger.error(f"Error getting date location: {e}")
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to get date location'
        }, status=500)


@csrf_exempt
def remove_date_location(request):
    """
    Remove/clear the date location from a date request
    """
    if not request.session.get('user_id'):
        return JsonResponse({'status': 'error', 'message': 'Not authenticated'}, status=401)
    
    userinfo(request)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
            request_id = data.get('request_id')
            
            if not request_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Missing request_id'
                }, status=400)
            
            # Find the date request
            date_request = DateReq.find_one({"_id": ObjectId(request_id)})
            if not date_request:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Date request not found'
                }, status=404)
            
            # Check if user is the sender
            if date_request.get('From') != name:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Only the sender can remove the date location'
                }, status=403)
            
            # Remove the date location
            result = DateReq.update_one(
                {"_id": ObjectId(request_id)},
                {"$unset": {"date_location": ""}}
            )
            
            if result.modified_count > 0:
                return JsonResponse({
                    'status': 'success',
                    'message': 'Date location removed successfully'
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Failed to remove date location'
                }, status=500)
                
        except Exception as e:
            logger.error(f"Error removing date location: {e}")
            return JsonResponse({
                'status': 'error',
                'message': 'Internal server error'
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Only POST method allowed'
    }, status=405)
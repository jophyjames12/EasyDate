
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

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['UserDetails']
users_collection = db['AccountHashing']
FriendReq = db['Friendrequest']
Friendlist = db['FriendList']
DateReq = db['DateRequests']  # New collection for date requests
Preference = db['PreferenceList']
Review=db['Reviews']
Location=db['Location']


#Add this function at the top of your views.py file after the MongoDB connections
def update_user_location(username, latitude, longitude):
    """
    Helper function to update or insert user location
    """
    try:
        # Convert lat/lon to float to ensure proper data type
        lat = float(latitude) if latitude else None
        lon = float(longitude) if longitude else None
        
        if lat is None or lon is None:
            print(f"Invalid coordinates for {username}: lat={latitude}, lon={longitude}")
            return False
        
        # Check if user location exists
        existing_location = Location.find_one({'name': username})
        
        if existing_location:
            # Update existing location
            result = Location.update_one(
                {'name': username}, 
                {'$set': {'lat': lat, 'lon': lon}}
            )
            print(f"Updated location for {username}: lat={lat}, lon={lon}")
            return result.modified_count > 0
        else:
            # Insert new location
            result = Location.insert_one({
                'name': username,
                'lat': lat,
                'lon': lon
            })
            print(f"Inserted new location for {username}: lat={lat}, lon={lon}")
            return result.inserted_id is not None
            
    except (ValueError, TypeError) as e:
        print(f"Error updating location for {username}: {e}")
        return False

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
    
    # Retrieve session flags for success messages
    account_created = request.session.get('account_created', False)
    login_success = request.session.get('login_success', False)
    
    # Clear session flags after displaying
    if 'account_created' in request.session:
        del request.session['account_created']
    
    if 'login_success' in request.session:
        del request.session['login_success']

    # Pass success messages to the template
    return render(request, 'MainApp/area.html', {'account_created': account_created, 'login_success': login_success})

# Logout view to end the user's session
def logout_view(request):
    if 'user_id' in request.session:
        # Remove user ID from session to log the user out
        del request.session['user_id']
    # Clear messages properly after the user logs out
    messages.get_messages(request).used = True  # This clears all messages
    return redirect('login')

# View to handle user search and friend request functionality
def search_user(request):
    userinfo(request)
    if request.method == "POST":
        username = request.POST.get('username')
        lat = request.POST.get('latitude')
        lon = request.POST.get('longitude')
        
        # Update user location with better error handling
        if lat and lon:
            location_updated = update_user_location(name, lat, lon)
            if not location_updated:
                messages.warning(request, "Failed to update your location.")
        else:
            messages.warning(request, "Location data not provided.")
        
        if not username:
            messages.error(request, "No username provided.")
            return redirect("search_user")
        
        target_user = users_collection.find_one({"username": username})
        if target_user:
            if username == name:
                messages.error(request, "You cannot send a friend request to yourself.")
                return redirect("search_user")
            
            existing_request = FriendReq.find_one({"From": name, "To": username}) or FriendReq.find_one({"From": username, "To": name})
            user_friendlist = Friendlist.find_one({"username": name})
            
            if user_friendlist and username in user_friendlist.get("friends", []):
                messages.info(request, "This user is already in your friend list.")
                return redirect("search_user")
            
            if existing_request:
                messages.info(request, "Friend request already sent. Waiting for response.")
                return redirect("search_user")
            
            friend_request = {"From": name, "To": username}
            FriendReq.insert_one(friend_request)
            messages.success(request, f"Friend request sent to {username}.")
            return redirect("search_user")
        
        messages.error(request, "User not found.")
        return redirect("search_user")
    
    friends = [friend["From"] for friend in FriendReq.find({"To": name})]
    user_friendlist = Friendlist.find_one({"username": name})
    all_friends = user_friendlist.get("friends", []) if user_friendlist else []
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

# Reject friend request by removing it from the database
def reject_request(request):
    if request.method == "POST":
        # Get the sender's username from the form data
        friendname = request.POST.get('friend_id')
        # Delete the friend request from the database
        FriendReq.delete_one({"From": friendname, "To": name})
        messages.success(request, f"Friend request from {friendname} rejected!")
    return redirect("search_user")

# Profile view to display the user's profile information
# --- New Features Below ---

# Send a date request to a friend with date and time input
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

        if friendname == name:
            messages.error(request, "You cannot send a date request to yourself.")
            return redirect('search_user')

        user_friendlist = Friendlist.find_one({"username": name})
        if not user_friendlist or friendname not in user_friendlist.get("friends", []):
            messages.error(request, "You can only send a date request to your friends.")
            return redirect('search_user')

        existing_date_request = DateReq.find_one({"From": name, "To": friendname}) or DateReq.find_one({"From": friendname, "To": name})

        if existing_date_request:
            messages.info(request, "Date request already sent. Waiting for response.")
            return redirect("search_user")

        date_request = {
            "From": name,
            "To": friendname,
            "status": "pending",
            "date": date,
            "time": time
        }
        DateReq.insert_one(date_request)
        messages.success(request, f"Date request sent to {friendname}.")
        return redirect("search_user")

# View pending date requests and show them on the profile page
# Profile view to display the user's profile information
# --- New Features Below ---
# View for displaying pending date requests and allowing the receiver to edit them
def profile(request):
    userinfo(request)

    # Fetch the pending date requests for the user
    sent_requests = DateReq.find({"From": name, "status": "pending"})
    received_requests = DateReq.find({"To": name, "status": "pending"})
    
    # Prepare lists of users that sent or received requests
    sent_from = [{"username": req["To"], "request_id": str(req["_id"])} for req in sent_requests]
    received_from = [{"username": req["From"], "request_id": str(req["_id"])} for req in received_requests]
    return render(request, 'MainApp/profile.html', {
        "sent_from": sent_from,
        "received_from": received_from
    })


    # Prepare received requests with date and time
    received_from = [
        {
            "username": req["From"],
            "request_id": str(req["_id"]),
            "date": req.get("date", ""),
            "time": req.get("time", "")
        }
        for req in received_requests
    ]
    return render(request, 'MainApp/profile.html', {"received_from": received_from})




# Helper to get user info
def userinfo(request):
    global user, name
    user = request.session.get('user_id')
    name = users_collection.find_one({"_id": ObjectId(user)}).get('username')

# Home view
def home(request):
    if not request.session.get('user_id'):
        return render(request, 'MainApp/login.html')
    return render(request, 'MainApp/area.html')

# Login view
def login_view(request):
    if request.session.get('user_id'):
        return render(request, 'MainApp/area.html')
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = users_collection.find_one({"username": username})
        if user and pbkdf2_sha256.verify(password, user['password']):
            request.session['user_id'] = str(user['_id'])
            request.session['login_success'] = True
            return redirect('area')
        else:
            messages.error(request, "Invalid username or password")
    return render(request, 'MainApp/login.html')

# Signup view
def signup_view(request):
    if request.session.get('user_id'):
        return redirect('area_view')
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        if password == confirm_password:
            if users_collection.find_one({"username": username}):
                messages.error(request, "Username already exists")
            elif users_collection.find_one({"email": email}):
                messages.error(request, "Email already registered")
            else:
                hashed_password = pbkdf2_sha256.hash(password)
                new_user = {
                    "username": username,
                    "email": email,
                    "password": hashed_password
                }
                users_collection.insert_one(new_user)
                request.session['user_id'] = str(new_user['_id'])
                request.session['account_created'] = True
                return redirect('area')
        else:
            messages.error(request, "Passwords do not match")
    return render(request, 'MainApp/signup.html')

# Area view
def area_view(request):
    if not request.session.get('user_id'):
        return redirect('login')
    account_created = request.session.get('account_created', False)
    login_success = request.session.get('login_success', False)
    if 'account_created' in request.session:
        del request.session['account_created']
    if 'login_success' in request.session:
        del request.session['login_success']
    return render(request, 'MainApp/area.html', {'account_created': account_created, 'login_success': login_success})

# Logout view
def logout_view(request):
    if 'user_id' in request.session:
        del request.session['user_id']
    messages.get_messages(request).used = True
    return redirect('login')

# Search and friend request
def search_user(request):
    userinfo(request)
    if request.method == "POST":
        username = request.POST.get('username')
        lat = request.POST.get('latitude')
        lon = request.POST.get('longitude')
        usename = Location.find_one({'name': name})
        if not usename:
            Location.insert_one({'name':name,'lat':lat,'lon':lon})
        else:
            Location.update_one({'_id': usename['_id']}, {'$set': {'lat': lat, 'lon': lon}})
        if not username:
            messages.error(request, "No username provided.")
            return redirect("search_user")
        
        target_user = users_collection.find_one({"username": username})
        if target_user:
            if username == name:
                messages.error(request, "You cannot send a friend request to yourself.")
                return redirect("search_user")
            
            existing_request = FriendReq.find_one({"From": name, "To": username}) or FriendReq.find_one({"From": username, "To": name})
            user_friendlist = Friendlist.find_one({"username": name})
            
            if user_friendlist and username in user_friendlist.get("friends", []):
                messages.info(request, "This user is already in your friend list.")
                return redirect("search_user")
            
            if existing_request:
                messages.info(request, "Friend request already sent. Waiting for response.")
                return redirect("search_user")
            
            friend_request = {"From": name, "To": username}
            FriendReq.insert_one(friend_request)
            messages.success(request, f"Friend request sent to {username}.")
            return redirect("search_user")
        
        messages.error(request, "User not found.")
        return redirect("search_user")
    
    friends = [friend["From"] for friend in FriendReq.find({"To": name})]
    user_friendlist = Friendlist.find_one({"username": name})
    all_friends = user_friendlist.get("friends", []) if user_friendlist else []
    return render(request, "MainApp/search.html", {"friends": friends, "all_friends": all_friends})

# Accept friend request
def accept_request(request):
    print("==== accept_request view reached ====")

    userinfo(request)
    print(f"Current user: {name}")  # Debug line
    if request.method == "POST":
        lat = request.POST.get('latitude')
        lon = request.POST.get('longitude')
        if lat and lon:
            try:
                lat = float(lat)
                lon = float(lon)
                Location.update_one({'name': name}, {'$set': {'lat': lat, 'lon': lon}}, upsert=True)
            except ValueError:
                print("Invalid coordinates received.")

        usename = Location.find_one({'name': name})
        if not usename:
            Location.insert_one({'name':name,'lat':lat,'lon':lon})
        else:
            Location.update_one({'_id': usename['_id']}, {'$set': {'lat': lat, 'lon': lon}})
        friendname = request.POST.get('friend_id')
        friend_request = FriendReq.find_one({"From": friendname, "To": name})
        if friend_request:
            sender = friend_request["From"]
            receiver = name
            Friendlist.update_one({"username": sender}, {"$addToSet": {"friends": receiver}}, upsert=True)
            Friendlist.update_one({"username": receiver}, {"$addToSet": {"friends": sender}}, upsert=True)
            FriendReq.delete_one({"From": friendname, "To": name})
            messages.success(request, f"You are now friends with {friendname}.")
    return redirect("search_user")

# Reject friend request
def reject_request(request):
    if request.method == "POST":
        friendname = request.POST.get('friend_id')
        FriendReq.delete_one({"From": friendname, "To": name})
        messages.success(request, f"Friend request from {friendname} rejected!")
    return redirect("search_user")

# Calculate midpoint between two users and find nearby places
@csrf_exempt
def calculate_midpoint(lat1, lon1, lat2, lon2):
    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Calculate the midpoint in radians
    bx = math.cos(lat2_rad) * math.cos(lon2_rad - lon1_rad)
    by = math.cos(lat2_rad) * math.sin(lon2_rad - lon1_rad)
    lat3_rad = math.atan2(math.sin(lat1_rad) + math.sin(lat2_rad),
                          math.sqrt((math.cos(lat1_rad) + bx) ** 2 + by ** 2))
    lon3_rad = lon1_rad + math.atan2(by, math.cos(lat1_rad) + bx)

    # Convert back to degrees
    lat3 = math.degrees(lat3_rad)
    lon3 = math.degrees(lon3_rad)

    return lat3, lon3

# Updated function to get midpoint and nearby places
def get_midpoint_and_nearby_places(request):
    if request.method == 'POST':
        try:
            user_lat = float(request.POST.get('user_lat'))
            user_lon = float(request.POST.get('user_lon'))
            friend_lat = float(request.POST.get('friend_lat'))
            friend_lon = float(request.POST.get('friend_lon'))

            # Calculate midpoint
            midpoint_lat, midpoint_lon = calculate_midpoint(user_lat, user_lon, friend_lat, friend_lon)

            # Get nearby places
            nearby_places = get_nearby_places(midpoint_lat, midpoint_lon)

            return JsonResponse({
                'midpoint': {'lat': midpoint_lat, 'lon': midpoint_lon},
                'nearby_places': nearby_places
            })

        except (ValueError, KeyError, TypeError) as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

def get_nearby_places(latitude, longitude, request):
    url = f"https://api.openstreetmap.org/api/0.6/map?bbox={longitude-0.01},{latitude-0.01},{longitude+0.01},{latitude+0.01}"
    response = request.get(url)
    if response.status_code == 200:
        return response.json().get('elements', [])
    return []


def handle_date_request(request):
    userinfo(request)

    if request.method == "POST":
        request_id = request.POST.get('request_id')
        action = request.POST.get('action')  # either 'accept' or 'reject'

        # Fetch the date request
        date_request = DateReq.find_one({"_id": ObjectId(request_id)})

        if date_request:
            if action == "accept":
                # Option to change the date or time before accepting
                new_date = request.POST.get('new_date', date_request["date"])
                new_time = request.POST.get('new_time', date_request["time"])
                
                # Update the date request with the new date/time if provided
                DateReq.update_one({"_id": ObjectId(request_id)}, {
                    "$set": {
                        "status": "accepted", 
                        "date": new_date, 
                        "time": new_time
                    }
                })
                messages.success(request, "Date request accepted.")
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
        
        return render(request, 'MainApp/area.html')
    else:
        return JsonResponse({"status": "error", "message": "Invalid request method."})

# View to handle saving preferences
#@csrf_exempt  # Temporarily exempt CSRF for testing, use CSRF middleware properly
#@login_required
#def save_preferences(request):
 #   if request.method == 'POST':
  #      data = json.loads(request.body)
   #     preferences = data.get('preferences', [])


        # Save preferences to the user model or a related model
    #    user = request.user
     #   user.preferences.set(preferences)  # Assuming you have a preferences field

@csrf_exempt
def get_places(request):
    places = list(places.objects.all().values())

    return JsonResponse(places, safe=False)


      #  return JsonResponse({"message": "Preferences saved successfully"})

   # return JsonResponse({"error": "Invalid request"}, status=400)

# Profile view to show user preferences
def profile_view(request):
    user = request.user
    preferences = user.preferences.all()  # Assuming the `preferences` field is a Many-to-Many relation
    return render(request, 'profile.html', {'user': user, 'preferences': preferences})

"""
            return JsonResponse({'status': 'success', 'message': 'Rating submitted successfully', 'rating': rating})

        except ValueError as ve:
            logger.error(f"Error: {ve}")
            return JsonResponse({'status': 'error', 'message': str(ve)}, status=400)
        except KeyError as ke:
            logger.error(f"Missing key error: {ke}")
            return JsonResponse({'status': 'error', 'message': f"Missing key: {str(ke)}"}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return JsonResponse({'status': 'error', 'message': 'Internal server error'}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

@csrf_exempt
def update_location(request):

    Dedicated endpoint for updating user location
    if request.method == 'POST':
        try:
            userinfo(request)  # Make sure userinfo sets 'name' globally or adjust accordingly
            
            # Support both JSON and form data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                lat = data.get('latitude')
                lon = data.get('longitude')
            else:
                lat = request.POST.get('latitude')
                lon = request.POST.get('longitude')
            
            if lat and lon:
                success = update_user_location(name, lat, lon)
                if success:
                    return JsonResponse({'status': 'success', 'message': 'Location updated'})
                else:
                    return JsonResponse({'status': 'error', 'message': 'Failed to update location'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Missing coordinates'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
"""

import json
import math
from asyncio.log import logger
from tkinter import Place
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from bson.objectid import ObjectId
from pymongo import MongoClient
from passlib.hash import pbkdf2_sha256  # For password hashing
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['UserDetails']
users_collection = db['AccountHashing']
FriendReq = db['Friendrequest']
Friendlist = db['FriendList']
DateReq = db['DateRequests']  
Review=db['Reviews']
Location=db['Location']
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
            # Delete the accepted friend request
            FriendReq.delete_one({"From": friendname, "To": name})
            messages.success(request, f"You are now friends with {friendname}.")
    return redirect("search_user")

# Reject friend request by removing it from the database
def reject_request(request):
    if request.method == "POST":
        # Get the sender's username from the form data
        friendname = request.POST.get('friend_id')
        # Delete the friend request from the database
        FriendReq.delete_one({"From": friendname, "To": name})
        messages.success(request, f"Friend request from {friendname} rejected!")
    return redirect("search_user")

# Send a date request to a friend with date and time input
def send_date_request(request):
    userinfo(request)
    if request.method == "POST":
        friendname = request.POST.get('friend_id')
        lat = request.POST.get('latitude')
        lon = request.POST.get('longitude')

        # Assuming you are searching for the user by some unique identifier (like 'name')
        try:
            # Fetch user location based on the name (or another identifier like 'friendname')
            usename = Location.find_one({'name': name})  # Make sure the correct field is used for lookup
        except:
            print("Error while fetching user location")
            return redirect('search_user')  # Handle case if the user is not found

        # Check if the user was found, if so, update the latitude and longitude
        if usename:
            usename['lat'] = lat
            usename['lon'] = lon

            # Update the user's location in the database (instead of inserting)
            Location.update_one({'_id': usename['_id']}, {'$set': {'lat': lat, 'lon': lon}})
        else:
            print("User not found in the Location collection")
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

        # Create a new date request with date and time
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
    # Only fetch pending date requests for the user
    received_requests = DateReq.find({"To": name, "status": "pending"})

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
    userinfo(request)
    if request.method == "POST":
        lat = request.POST.get('latitude')
        lon = request.POST.get('longitude')
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

# Map view to show midpoint
def map_view(request):
    Rev = Review.find()
    return render(request, 'MainApp/Map.html', {'reviews': Rev})
    
# Saving preferences
def save_preferences(request):
    if request.method == 'POST':
        preferences = request.POST.getlist('preferences[]')
        user = request.user
        user.preferences.set(preferences)
        user.save()
        return JsonResponse({'success': True})

# Profile view to show preferences
def profile_view(request):
    user = request.user
    preferences = user.preferences.all()
    return render(request, 'profile.html', {'user': user, 'preferences': preferences})

@csrf_exempt
def rate_place(request):
    if request.method == 'POST':
        try:
            # Parse the JSON data from the frontend
            data = json.loads(request.body)

            # Ensure all required fields are present
            place_id = data.get('placeId')
            rating = data.get('rating')
            latitude = data.get('lat')
            longitude = data.get('lon')

            if not place_id or not rating or not latitude or not longitude:
                logger.error("Missing required fields")
                return JsonResponse({'status': 'error', 'message': 'Missing required fields'}, status=400)

            # Storing in DB
            existing_review = Review.find_one({"name": place_id, "lat": latitude, "lon": longitude})
            
            if existing_review:  # Check if it exists
                total_ratings = existing_review.get("total_ratings", 0) + 1
                avg_rating = (existing_review.get("average_rating", 0) * existing_review.get("total_ratings", 0) + rating) / total_ratings
                # Update the review entry
                Review.update_one(
                    {"_id": existing_review["_id"]}, 
                    {"$set": {"average_rating": avg_rating, "total_ratings": total_ratings}}
                )
            else:
                # Insert a new review if it doesn't exist
                Review.insert_one({
                    "name": place_id,
                    "lat": latitude,
                    "lon": longitude,
                    "total_ratings": 1,
                    "average_rating": rating
                })

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

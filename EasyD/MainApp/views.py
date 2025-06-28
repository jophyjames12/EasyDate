
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

@csrf_exempt
def update_location(request):
    userinfo(request)
    if request.method == 'POST':
        lat = request.POST.get('latitude')
        lon = request.POST.get('longitude')
        if lat and lon:
            existing = Location.find_one({'name': name})
            if existing:
                Location.update_one({'_id': existing['_id']}, {'$set': {'lat': lat, 'lon': lon}})
            else:
                Location.insert_one({'name': name, 'lat': lat, 'lon': lon})
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'error', 'message': 'Missing coordinates'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


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
    # Retrieve session flags for success messages
    account_created = request.session.get('account_created', False)
    login_success = request.session.get('login_success', False)
    
    # Clear session flags after displaying
    if 'account_created' in request.session:
        del request.session['account_created']
    
    if 'login_success' in request.session:
        del request.session['login_success']
    
    # Fetch accepted dates for the current user
    accepted_dates = list(DateReq.find({
        "$or": [
            {"From": name, "status": "accepted"},
            {"To": name, "status": "accepted"}
        ]
    }))

    # Process dates to get partner info
    processed_dates = []
    for date_req in accepted_dates:
        partner = date_req["To"] if date_req["From"] == name else date_req["From"]
        processed_dates.append({
            'date': date_req.get('date', ''),
            'time': date_req.get('time', ''),
            'partner': partner,
            'request_id': str(date_req['_id'])
        })

    # Pass success messages and accepted dates to the template
    return render(request, 'MainApp/area.html', {
        'account_created': account_created, 
        'login_success': login_success,
        'accepted_dates': processed_dates
    })

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
                
                # Update the date request with the new date/time
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

        if lat is None or lon is None:
            return JsonResponse({'status': 'error', 'message': 'Missing latitude or longitude'}, status=400)

        try:
            lat = float(lat)
            lon = float(lon)
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Invalid latitude or longitude'}, status=400)

        existing = Location.find_one({'name': name})
        if existing:
            Location.update_one({'_id': existing['_id']}, {'$set': {'lat': lat, 'lon': lon}})
        else:
            Location.insert_one({'name': name, 'lat': lat, 'lon': lon})

        return JsonResponse({'status': 'success', 'message': 'Location updated successfully'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

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
    
    # Get both users' locations
    user_location = Location.find_one({'name': name})
    partner_location = Location.find_one({'name': partner})
    
    # Prepare date info
    date_info_dict = {
        'date': date_request.get('date', ''),
        'time': date_request.get('time', ''),
        'partner': partner,
        'user_lat': float(user_location['lat']) if user_location else None,
        'user_lon': float(user_location['lon']) if user_location else None,
        'partner_lat': float(partner_location['lat']) if partner_location else None,
        'partner_lon': float(partner_location['lon']) if partner_location else None,
    }
    
    context = {
        'date_info': date_info_dict,
        'date_info_json': json.dumps(date_info_dict),  # Add JSON serialized version
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

   
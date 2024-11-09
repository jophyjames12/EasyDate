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
import json

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

# Profile view to display the user's profile information
# --- New Features Below ---

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
    Rev=Review.find()
    return render(request,'MainApp/Map.html',{'reviews': Rev})
    
# View to handle saving preferences
def save_preferences(request):
    if request.method == 'POST':
        preferences = request.POST.getlist('preferences[]')  # List of selected preferences
        # Assuming the user is logged in and the user model has a `preferences` field
        user = request.user
        user.preferences.set(preferences)
        user.save()
        return JsonResponse({'success': True})

# Profile view to show user preferences
def profile_view(request):
    user = request.user
    preferences = user.preferences.all()  # Assuming the `preferences` field is a Many-to-Many relation
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

            #storing in db
            existing_review = Review.find_one({"name": place_id, "lat": latitude, "lon": longitude})
            
            if existing_review:#check if it exists
                 total_ratings = existing_review.get("total_ratings", 0) + 1
                 avg_rating = (existing_review.get("average_rating", 0) * existing_review.get("total_ratings", 0) + rating) / total_ratings
                # Update the review entry
                 Review.update_one(
                    {"_id": existing_review["_id"]}, 
                    {"$set": {"average_rating": avg_rating, "total_ratings": total_ratings}}
                 
                 )
            else:
                Review.insert_one({
                "name": place_id,
                "lat": latitude,
                "lon": longitude,
                "total_ratings": 1,
                "average_rating": rating
                })         

            return JsonResponse({'status': 'success', 'message': 'Rating submitted successfully','rating':rating})

        except ValueError as ve:
            logger.error(f"Error: {ve}")
            return JsonResponse({'status': 'error', 'message': str(ve)}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return JsonResponse({'status': 'error', 'message': 'Internal server error'}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)


@csrf_exempt
def get_places(request):
    places = list(places.objects.all().values())

    return JsonResponse(places, safe=False)

@csrf_exempt
def sort_places_by_reviews(request):
    if request.method == 'POST':
        try:
            # Parse the JSON data from the frontend
            data = json.loads(request.body)

            # Extract the list of places (lat, lon, name) from the frontend
            places = data.get('places', [])
            
            if not places:
                return JsonResponse({'status': 'error', 'message': 'No places data provided'}, status=400)

            # Fetch ratings for each place and sort them by the average_rating
            sorted_places = []
            for place in places:
                # Assuming place contains lat, lon, and name to find the review
                review = Review.find_one({
                    "lat": place['lat'],
                    "lon": place['lon'],
                    "name": place['name']
                })
                
                # If the place has a review, append it with the average rating
                if review:
                    place['average_rating'] = review.get('average_rating', 0)
                else:
                    place['average_rating'] = 0  # Default to 0 if no review exists
                
                sorted_places.append(place)

            # Sort the places by average_rating
            sorted_places.sort(key=lambda x: x.get('average_rating', 0), reverse=True)
            
            return JsonResponse({'status': 'success', 'sorted_places': sorted_places})

        except ValueError as ve:
            logger.error(f"Error: {ve}")
            return JsonResponse({'status': 'error', 'message': str(ve)}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return JsonResponse({'status': 'error', 'message': 'Internal server error'}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)


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
from PIL import Image
from django.core.files.storage import FileSystemStorage
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.shortcuts import render, redirect
from django.contrib import messages
from datetime import datetime, date, timedelta
from passlib.hash import pbkdf2_sha256
from datetime import datetime, timedelta

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
Events = db['Events']  # New collection for events
EventImages = db['EventImages']  # New collection for event images
OldEvents = db['OldEvents']

GOOGLE_CLIENT_ID = "633306351645-t7fp851eg57ta2r0jhelc87qnlb02b3j.apps.googleusercontent.com"  # Replace this
@csrf_exempt
def google_auth_view(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

    try:
        data = json.loads(request.body)
        credential = data.get('credential')

        if not credential:
            return JsonResponse({'success': False, 'error': 'Missing credential'})

        # Verify token with Google
        token_info = requests.get(f'https://oauth2.googleapis.com/tokeninfo?id_token={credential}').json()

        if token_info.get('aud') != GOOGLE_CLIENT_ID:
            return JsonResponse({'success': False, 'error': 'Token audience mismatch'}, status=400)

        email = token_info.get('email')
        name = token_info.get('name')

        if not email:
            return JsonResponse({'success': False, 'error': 'Email not found in token'}, status=400)

        # Check if user exists in MongoDB
        user = users_collection.find_one({"email": email})

        if not user:
            # New user from Google Sign-In
            user_data = {
            "username": name,  # Full name from Google
            "email": email,
            "password": None,  # No password because it's Google Sign-In
            "login_method": "google"
            }
            inserted = users_collection.insert_one(user_data)
            user_id = str(inserted.inserted_id)
        else:
            user_id = str(user["_id"])

        # Set Django session
        request.session['user_id'] = user_id
        request.session['login_success'] = True

        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
# Events view - main events page
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

def send_otp_email(email, otp):
    """Send OTP to user's email"""
    try:
        # Configure your email settings
        smtp_server = settings.EMAIL_HOST
        smtp_port = settings.EMAIL_PORT
        sender_email = settings.EMAIL_HOST_USER
        sender_password = settings.EMAIL_HOST_PASSWORD
        
        # Create message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = email
        message["Subject"] = "Email Verification - Your OTP Code"
        
        # Email body
        body = f"""
        Hi there!
        
        Your verification code is: {otp}
        
        This code will expire in 10 minutes.
        
        If you didn't request this code, please ignore this email.
        
        Best regards,
        Your App Team
        """
        
        message.attach(MIMEText(body, "plain"))
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)
        
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def generate_otp():
    """Generate a 6-digit OTP"""
    return str(random.randint(100000, 999999))

def signup_view(request):
    # Redirects logged-in users to the main area page
    if request.session.get('user_id'):
        return redirect('area_view')

    if request.method == 'POST':
        # Check if this is OTP verification step
        if request.POST.get('step') == 'verify_otp':
            return handle_otp_verification(request)
        
        # This is the initial registration step
        return handle_initial_registration(request)
    
    return render(request, 'MainApp/signup.html')

def handle_initial_registration(request):
    """Handle the initial registration form submission"""
    # Retrieve form data for user registration
    username = request.POST['username']
    email = request.POST['email']
    password = request.POST['password']
    confirm_password = request.POST['confirm_password']

    # Check if passwords match
    if password != confirm_password:
        messages.error(request, "Passwords do not match")
        return render(request, 'MainApp/signup.html')

    # Check if username or email already exists in MongoDB
    if users_collection.find_one({"username": username}):
        messages.error(request, "Username already exists")
        return render(request, 'MainApp/signup.html')
    elif users_collection.find_one({"email": email}):
        messages.error(request, "Email already registered")
        return render(request, 'MainApp/signup.html')

    # Generate OTP
    otp = generate_otp()
    
    # Store user data and OTP in session temporarily
    request.session['pending_user'] = {
        'username': username,
        'email': email,
        'password': password,
        'otp': otp,
        'otp_created_at': datetime.now().isoformat()
    }
    
    # Send OTP via email
    if send_otp_email(email, otp):
        messages.success(request, f"Verification code sent to {email}")
        return render(request, 'MainApp/signup.html', {'show_otp_form': True})
    else:
        messages.error(request, "Failed to send verification email. Please try again.")
        return render(request, 'MainApp/signup.html')

def handle_otp_verification(request):
    """Handle OTP verification step"""
    entered_otp = request.POST.get('otp')
    pending_user = request.session.get('pending_user')
    
    if not pending_user:
        messages.error(request, "Session expired. Please start registration again.")
        return render(request, 'MainApp/signup.html')
    
    # Check if OTP has expired (10 minutes)
    otp_created_at = datetime.fromisoformat(pending_user['otp_created_at'])
    if datetime.now() - otp_created_at > timedelta(minutes=10):
        messages.error(request, "OTP has expired. Please start registration again.")
        del request.session['pending_user']
        return render(request, 'MainApp/signup.html')
    
    # Verify OTP
    if entered_otp == pending_user['otp']:
        # OTP is correct, create the user
        hashed_password = pbkdf2_sha256.hash(pending_user['password'])
        new_user = {
            "username": pending_user['username'],
            "email": pending_user['email'],
            "password": hashed_password,
            "login_method": "password",
            "email_verified": True,
            "created_at": datetime.now()
        }
        
        result = users_collection.insert_one(new_user)
        
        # Start session for the newly registered user
        request.session['user_id'] = str(result.inserted_id)
        request.session['account_created'] = True
        
        # Clean up pending user data
        del request.session['pending_user']
        
        messages.success(request, "Registration successful! Welcome!")
        return redirect('area')
    else:
        messages.error(request, "Invalid OTP. Please try again.")
        return render(request, 'MainApp/signup.html', {'show_otp_form': True})

def resend_otp(request):
    """Resend OTP to user's email"""
    if request.method == 'POST':
        pending_user = request.session.get('pending_user')
        
        if not pending_user:
            messages.error(request, "Session expired. Please start registration again.")
            return redirect('signup')
        
        # Generate new OTP
        otp = generate_otp()
        
        # Update session with new OTP
        pending_user['otp'] = otp
        pending_user['otp_created_at'] = datetime.now().isoformat()
        request.session['pending_user'] = pending_user
        
        # Send new OTP
        if send_otp_email(pending_user['email'], otp):
            messages.success(request, "New verification code sent!")
        else:
            messages.error(request, "Failed to send verification email. Please try again.")
        
        return render(request, 'MainApp/signup.html', {'show_otp_form': True})
    
    return redirect('signup')

def logout_view(request):
    if 'user_id' in request.session:
        # Remove user ID from session to log the user out
        del request.session['user_id']
    # Clear messages properly after the user logs out
    messages.get_messages(request).used = True  # This clears all messages
    return redirect('login')


#----------------------------------------------------------------------------------------------------------------------------

# Area view to display main content for logged-in users
def area_view(request):
    if not request.session.get('user_id'):
        return redirect('login')
    
    # Get user info
    userinfo(request)
    
    # Move old dates to separate collection
    move_old_dates()
    
    # Move old events to separate collection (ADD THIS LINE)
    move_old_events()
    
    # Rest of your existing area_view code stays the same...
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

    # Fetch recent approved events (last 3 for homepage display)
    # UPDATE: Only show current/future events on homepage
    today = date.today().strftime('%Y-%m-%d')
    recent_events = list(Events.find({
        'status': 'approved',
        '$or': [
            {'event_date': {'$gte': today}},  # Future events
            {'event_date': {'$exists': False}},  # Events without date
            {'event_date': ""}  # Events with empty date
        ]
    }).sort('created_at', -1).limit(3))
    
    # Process recent events to add image URLs
    for event in recent_events:
        event['id'] = str(event['_id'])
        # Get first image for display
        event_images = EventImages.find({'event_id': str(event['_id'])}).limit(1)
        first_image = next(event_images, None)
        event['image'] = first_image['image_url'] if first_image else None

    # Rest of your existing code for processing dates...
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
    
    # Pass success messages, dates, and events to the template
    return render(request, 'MainApp/area.html', {
        'account_created': account_created, 
        'login_success': login_success,
        'upcoming_dates': processed_upcoming_dates,
        'old_dates': processed_old_dates,
        'accepted_dates': processed_upcoming_dates,  # Keep for backward compatibility
        'recent_events': recent_events,  # Only current/future events
    })

def past_events_view(request):
    """View to display all past events for the user"""
    if not request.session.get('user_id'):
        return redirect('login')
    
    userinfo(request)
    
    # Move old events to separate collection
    move_old_events()
    
    # Fetch all past events
    past_events = list(OldEvents.find({
        '$or': [
            {'created_by': name},  # Events created by user
            {'status': 'approved'}  # All approved past events (community events)
        ]
    }).sort("moved_at", -1))
    
    # Process past events to add image URLs
    for event in past_events:
        event['id'] = str(event.get('_id', event.get('original_id', '')))
        # Get first image for display
        event_id = str(event.get('_id', event.get('original_id', '')))
        event_images = EventImages.find({'event_id': event_id}).limit(1)
        first_image = next(event_images, None)
        event['image'] = first_image['image_url'] if first_image else None
    
    return render(request, 'MainApp/past_events.html', {
        'past_events': past_events,
        'name': name
    })

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

#-------------------------------------------------------------------------------------------------------------------
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

#------------------------------------------------------------------------------------------------------------------------------
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
            "can_set_location": req.get("date_location") is not None  # Receiver can change existing location
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
            "can_set_location": is_sender or (not is_sender and req.get("date_location") is not None),  # Updated permission logic
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

#------------------------------------------------------------------------------------------------------------------------------
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
            preferred_tags = ['restaurant', 'cafe', 'bar', 'club', 'Malls']
            logger.info("No preferences found, using default tags")
        
        # Map preferences to amenity tags
        preference_to_amenity = {
            'restaurant': 'restaurant',
            'cafe': 'cafe', 
            'bar': 'bar',
            'club': 'club',
            'malls': 'shop=mall'
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

def fetch_overpass_places(lat, lon, amenity_type=None, radius=3000):
    # Add coordinate validation
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        logger.error(f"Invalid coordinates: lat={lat}, lon={lon}")
        return []

    # DEBUG: Print what we're actually receiving
    logger.info(f"DEBUG: amenity_type = '{amenity_type}', type = {type(amenity_type)}")
    logger.info(f"DEBUG: amenity_type == 'malls': {amenity_type == 'malls'}")
    logger.info(f"DEBUG: amenity_type is None: {amenity_type is None}")

    # If searching for malls, use custom query
    if amenity_type == "malls" or amenity_type is None:
        logger.info("DEBUG: Using mall search query")
        query = f"""
        [out:json][timeout:200];
        (
          node["name"~"mall|shopping|plaza|center|centre|complex",i](around:{radius},{lat},{lon});
          way["name"~"mall|shopping|plaza|center|centre|complex",i](around:{radius},{lat},{lon});
          relation["name"~"mall|shopping|plaza|center|centre|complex",i](around:{radius},{lat},{lon});
        );
        out center;
        """
    else:
        logger.info(f"DEBUG: Using amenity search for '{amenity_type}'")
        # fallback: use amenity tag (e.g., amenity=restaurant, etc.)
        query = f"""
        [out:json][timeout:25];
        (
          node["amenity"="{amenity_type}"](around:{radius},{lat},{lon});
          way["amenity"="{amenity_type}"](around:{radius},{lat},{lon});
          relation["amenity"="{amenity_type}"](around:{radius},{lat},{lon});
        );
        out center;
        """

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
    
    # Prepare current location data for JSON serialization (if it exists)
    current_location = date_request.get('date_location', None)
    if current_location and 'selected_at' in current_location:
        # Convert datetime to string for JSON serialization
        current_location_copy = current_location.copy()
        current_location_copy['selected_at'] = current_location['selected_at'].isoformat() if isinstance(current_location['selected_at'], datetime) else str(current_location['selected_at'])
        current_location = current_location_copy
    
    # NEW: Check if there's a date location set
    has_date_location = current_location is not None
    
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
        'current_location': current_location,
        'has_date_location': has_date_location,
        'show_routes_to_location': has_date_location,
        'auto_search_places': False  # NEW: Disable auto-search for regular date mode too
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

def move_old_events():
    """Move events that have passed their event date to OldEvents collection"""
    try:
        today = date.today()
        old_events = Events.find({
            "status": "approved",  # Only move approved events
            "event_date": {"$exists": True, "$ne": ""}
        })
        
        moved_count = 0
        for event in old_events:
            try:
                # Parse the event date string (assuming format YYYY-MM-DD)
                event_date_str = event.get('event_date', '')
                if event_date_str:
                    # Handle different date formats
                    try:
                        event_date_obj = datetime.strptime(event_date_str, '%Y-%m-%d').date()
                    except ValueError:
                        try:
                            event_date_obj = datetime.strptime(event_date_str, '%m/%d/%Y').date()
                        except ValueError:
                            try:
                                event_date_obj = datetime.strptime(event_date_str, '%d/%m/%Y').date()
                            except ValueError:
                                continue  # Skip if date format is not recognized
                    
                    # Check if event date has passed
                    if event_date_obj < today:
                        # Add to OldEvents collection
                        old_event_doc = dict(event)
                        old_event_doc['moved_at'] = datetime.now()
                        old_event_doc['original_id'] = event['_id']
                        
                        # Insert into OldEvents
                        OldEvents.insert_one(old_event_doc)
                        
                        # Remove from Events
                        Events.delete_one({"_id": event['_id']})
                        moved_count += 1
                        
            except Exception as e:
                logger.error(f"Error processing event {event.get('_id')}: {e}")
                continue
        
        logger.info(f"Moved {moved_count} old events to OldEvents collection")
        return moved_count
        
    except Exception as e:
        logger.error(f"Error in move_old_events: {e}")
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
            
            # Updated permission check: sender can always set/change, receiver can only change existing location
            is_sender = date_request.get('From') == name
            is_receiver = date_request.get('To') == name
            existing_location = date_request.get('date_location')

            if not (is_sender or is_receiver):
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Access denied'
                }, status=403)

            # Receiver can only change existing location, not set initial location
            if is_receiver and not existing_location:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Only the sender can set the initial date location'
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


def auto_select_midpoint_restaurant(request):
    """
    Automatically select the closest restaurant to the midpoint between two users
    """
    if not request.session.get('user_id'):
        return JsonResponse({'status': 'error', 'message': 'Not authenticated'}, status=401)

    userinfo(request)

    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
            request_id = data.get('request_id')

            if not request_id:
                return JsonResponse({'status': 'error', 'message': 'Missing request_id'}, status=400)

            date_request = DateReq.find_one({"_id": ObjectId(request_id)})
            if not date_request:
                return JsonResponse({'status': 'error', 'message': 'Date request not found'}, status=404)

            is_sender = date_request.get('From') == name
            is_receiver = date_request.get('To') == name
            existing_location = date_request.get('date_location')

            if not (is_sender or is_receiver):
                return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)

            if is_receiver and not existing_location:
                return JsonResponse({'status': 'error', 'message': 'Only the sender can set the initial date location'}, status=403)

            partner = date_request["To"] if date_request["From"] == name else date_request["From"]

            user_location = Location.find_one({'name': name})
            partner_location = Location.find_one({'name': partner})

            if not user_location or not partner_location:
                return JsonResponse({'status': 'error', 'message': 'User locations not found'}, status=404)

            try:
                user_lat = float(user_location['lat'])
                user_lon = float(user_location['lon'])
                partner_lat = float(partner_location['lat'])
                partner_lon = float(partner_location['lon'])
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'Invalid location coordinates'}, status=400)

            route_midpoint_lat, route_midpoint_lon = get_route_midpoint(user_lat, user_lon, partner_lat, partner_lon)

            preferred_tags = get_combined_preferences(name, partner)
            if not preferred_tags:
                preferred_tags = ['restaurant']

            closest_restaurant = find_closest_restaurant(route_midpoint_lat, route_midpoint_lon, preferred_tags)

            if not closest_restaurant:
                return JsonResponse({'status': 'error', 'message': 'No restaurants found near the midpoint'}, status=404)

            location_data = {
                'name': closest_restaurant['name'],
                'lat': closest_restaurant['lat'],
                'lon': closest_restaurant['lon'],
                'address': closest_restaurant.get('address', ''),
                'type': closest_restaurant.get('type', 'restaurant'),
                'selected_by': name,
                'selected_at': datetime.now(),
                'auto_selected': True,
                'distance_from_midpoint': closest_restaurant.get('distance', 0)
            }

            result = DateReq.update_one({"_id": ObjectId(request_id)}, {"$set": {"date_location": location_data}})

            if result.modified_count > 0:
                return JsonResponse({
                    'status': 'success',
                    'message': f'Auto-selected restaurant: {closest_restaurant["name"]}',
                    'location': location_data,
                    'midpoint': {'lat': route_midpoint_lat, 'lon': route_midpoint_lon}
                })
            else:
                return JsonResponse({'status': 'error', 'message': 'Failed to update date location'}, status=500)

        except Exception as e:
            logger.error(f"Error auto-selecting restaurant: {e}")
            return JsonResponse({'status': 'error', 'message': 'Internal server error'}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Only POST method allowed'}, status=405)


def get_route_midpoint(user_lat, user_lon, partner_lat, partner_lon):
    """
    Get the actual route midpoint between two locations
    """
    try:
        import requests
        url = f"https://router.project-osrm.org/route/v1/driving/{user_lon},{user_lat};{partner_lon},{partner_lat}?overview=full&geometries=geojson"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('routes') and len(data['routes']) > 0:
                coords = data['routes'][0]['geometry']['coordinates']
                midpoint_index = len(coords) // 2
                route_midpoint_lon, route_midpoint_lat = coords[midpoint_index]
                return route_midpoint_lat, route_midpoint_lon

    except Exception as e:
        logger.warning(f"Failed to get route midpoint: {e}")

    # Fallback to geographic midpoint
    midpoint_lat = (user_lat + partner_lat) / 2
    midpoint_lon = (user_lon + partner_lon) / 2
    return midpoint_lat, midpoint_lon

def find_closest_restaurant(midpoint_lat, midpoint_lon, preferred_tags):
    """
    Find the closest place to the midpoint based on user preferences (restaurant, cafe, malls, etc.)
    """
    try:
        preference_to_amenity = {
            'restaurant': 'amenity=restaurant',
            'cafe': 'amenity=cafe',
            'bar': 'amenity=bar',
            'club': 'amenity=nightclub',
            'malls': ['shop=mall', 'shop=shopping_centre']
        }

        amenity_tags = []
        for pref in preferred_tags:
            tag_value = preference_to_amenity.get(pref)
            if tag_value:
                if isinstance(tag_value, list):
                    amenity_tags.extend(tag_value)
                else:
                    amenity_tags.append(tag_value)

        if not amenity_tags:
            amenity_tags = ['amenity=restaurant']

        all_places = []
        for tag in amenity_tags:
            places = fetch_overpass_places(midpoint_lat, midpoint_lon, tag)
            all_places.extend(places)

        if not all_places:
            return None

        closest_place = None
        min_distance = float('inf')

        for place in all_places:
            tags = place.get('tags', {})
            place_lat = place.get('lat') or (place.get('center', {}).get('lat'))
            place_lon = place.get('lon') or (place.get('center', {}).get('lon'))

            if place_lat and place_lon:
                distance = calculate_distance(midpoint_lat, midpoint_lon, float(place_lat), float(place_lon))

                if distance < min_distance:
                    min_distance = distance
                    address_parts = [
                        tags.get('addr:housenumber'),
                        tags.get('addr:street'),
                        tags.get('addr:city')
                    ]
                    address = ', '.join(filter(None, address_parts))

                    closest_place = {
                        'name': tags.get('name', 'Unknown'),
                        'lat': float(place_lat),
                        'lon': float(place_lon),
                        'address': address,
                        'type': tags.get('amenity') or tags.get('shop') or 'restaurant',
                        'distance': distance
                    }

        return closest_place

    except Exception as e:
        logger.error(f"Error finding closest restaurant: {e}")
        return None

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points on Earth (in km)
    """
    import math
    
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    
    return c * r


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
                'can_set_location': is_sender or (not is_sender and date_req.get('date_location') is not None),  # Updated permission logic
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
    
    # Updated permission check: sender can always select, receiver can only change existing location
    is_sender = date_request.get('From') == name
    is_receiver = date_request.get('To') == name
    existing_location = date_request.get('date_location')

    if not (is_sender or is_receiver):
        messages.error(request, "Access denied.")
        return redirect('area')

    if is_receiver and not existing_location:
        messages.error(request, "Only the sender can set the initial date location.")
        return redirect('area')
    
    # Get partner info
    partner = date_request["To"] if date_request["From"] == name else date_request["From"]
    
    # Get both users' locations with detailed error checking
    user_location = Location.find_one({'name': name})
    partner_location = Location.find_one({'name': partner})
    
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
    
    # Get combined preferences for context
    preferred_tags = get_combined_preferences(name, partner)
    
    # Prepare current location data for JSON serialization
    current_location = date_request.get('date_location', None)
    if current_location and 'selected_at' in current_location:
        # Convert datetime to string for JSON serialization
        current_location_copy = current_location.copy()
        current_location_copy['selected_at'] = current_location['selected_at'].isoformat() if isinstance(current_location['selected_at'], datetime) else str(current_location['selected_at'])
        current_location = current_location_copy
    
    # NEW: Get route midpoint (not just coordinate midpoint)
    route_midpoint_lat = None
    route_midpoint_lon = None
    
    # Try to get actual route midpoint
    try:
        import requests
        url = f"https://router.project-osrm.org/route/v1/driving/{user_lon},{user_lat};{partner_lon},{partner_lat}?overview=full&geometries=geojson"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('routes') and len(data['routes']) > 0:
                route = data['routes'][0]
                if route.get('geometry') and route['geometry'].get('coordinates'):
                    coords = route['geometry']['coordinates']
                    # Get the actual midpoint of the route
                    midpoint_index = len(coords) // 2
                    route_midpoint_lon, route_midpoint_lat = coords[midpoint_index]
                    logger.info(f"Route midpoint found: {route_midpoint_lat}, {route_midpoint_lon}")
    except Exception as e:
        logger.warning(f"Failed to get route midpoint: {e}")
    
    # Fallback to coordinate midpoint if route fails
    if route_midpoint_lat is None or route_midpoint_lon is None:
        route_midpoint_lat = (user_lat + partner_lat) / 2
        route_midpoint_lon = (user_lon + partner_lon) / 2
        logger.info(f"Using coordinate midpoint fallback: {route_midpoint_lat}, {route_midpoint_lon}")
    
    # Prepare date info with location selection mode
    date_info_dict = {
        'request_id': str(date_request['_id']),
        'date': date_request.get('date', ''),
        'time': date_request.get('time', ''),
        'partner': partner,
        'status': date_request.get('status', ''),
        'user_lat': user_lat,
        'user_lon': user_lon,
        'partner_lat': partner_lat,
        'partner_lon': partner_lon,
        'route_midpoint_lat': route_midpoint_lat,  # NEW: Actual route midpoint
        'route_midpoint_lon': route_midpoint_lon,  # NEW: Actual route midpoint
        'preferred_tags': preferred_tags,
        'mode': 'location_selection',  # Special mode for location selection
        'current_location': current_location,
        'is_sender': is_sender,  # NEW: Add sender flag
        'show_midpoint_route': not current_location  # NEW: Show midpoint route only if no location set
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
        is_sender = date_request.get('From') == name
        
        return JsonResponse({
            'status': 'success',
            'date_location': date_location,
            'can_modify': is_sender or (not is_sender and date_location is not None)  # Updated permission logic
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
            
            # Updated permission check: both sender and receiver can remove existing location
            is_sender = date_request.get('From') == name
            is_receiver = date_request.get('To') == name

            if not (is_sender or is_receiver):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Access denied'
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

#-----------------------------------------------------------------------------------------------------------------------
# Create event view
@csrf_exempt
def create_event(request):
    if not request.session.get('user_id'):
        return redirect('login')
    
    userinfo(request)
    
    if request.method == 'POST':
        try:
            # Get form data
            event_name = request.POST.get('event_name', '').strip()
            event_description = request.POST.get('event_description', '').strip()
            event_date = request.POST.get('event_date', '').strip()
            event_time = request.POST.get('event_time', '').strip()
            event_location = request.POST.get('event_location', '').strip()
            event_lat = request.POST.get('event_lat', '')
            event_lon = request.POST.get('event_lon', '')
            
            # Validate required fields
            if not event_name or not event_description or not event_date:
                messages.error(request, "Event name, description, and date are required.")
                return redirect('events')
            
            # Create event document
            event_data = {
                'name': event_name,
                'description': event_description,
                'event_date': event_date,
                'event_time': event_time,
                'location': event_location,
                'created_by': name,
                'status': 'pending',  # All events start as pending
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            # Add location coordinates if provided
            if event_lat and event_lon:
                try:
                    event_data['lat'] = float(event_lat)
                    event_data['lon'] = float(event_lon)
                except ValueError:
                    pass  # Skip if coordinates are invalid
            
            # Insert event into database
            result = Events.insert_one(event_data)
            event_id = str(result.inserted_id)
            
            # Handle image uploads
            uploaded_files = request.FILES.getlist('event_images')
            image_count = 0
            # DEBUG: Add logging to see what files are received
            print(f"DEBUG: Found {len(uploaded_files)} uploaded files")
            for i, file in enumerate(uploaded_files):
                print(f"  File {i+1}: {file.name}, Size: {file.size}, Type: {file.content_type}")
            
            for uploaded_file in uploaded_files:
                if uploaded_file and image_count < 5:  # Limit to 5 images
                    try:
                        # Validate file type
                        if not uploaded_file.content_type.startswith('image/'):
                            continue
                        
                        # Validate file size (5MB limit)
                        if uploaded_file.size > 5 * 1024 * 1024:
                            continue
                        
                        # Create upload directory
                        upload_dir = os.path.join(settings.MEDIA_ROOT, 'event_images')
                        if not os.path.exists(upload_dir):
                            os.makedirs(upload_dir, mode=0o755)
                        
                        # Generate unique filename
                        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        unique_id = str(uuid.uuid4())[:8]
                        filename = f"event_{event_id}_{timestamp}_{unique_id}{file_extension}"
                        file_path = os.path.join(upload_dir, filename)
                        
                        # Save file
                        with open(file_path, 'wb+') as destination:
                            for chunk in uploaded_file.chunks():
                                destination.write(chunk)
                        
                        # Store image info in database
                        image_url = f"/media/event_images/{filename}"
                        EventImages.insert_one({
                            'event_id': event_id,
                            'image_url': image_url,
                            'filename': filename,
                            'uploaded_at': datetime.now()
                        })
                        
                        image_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error uploading image: {e}")
                        continue
            
            messages.success(request, f"Event '{event_name}' has been submitted for approval!")
            return redirect('events')
            
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            messages.error(request, "An error occurred while creating the event. Please try again.")
            return redirect('events')
    
    return redirect('events')

# Approve event view (admin only)
@csrf_exempt
def approve_event(request):
    if not request.session.get('user_id'):
        return redirect('login')
    
    userinfo(request)
    
    # Check if user is admin
    if name not in ['Faisal', 'Jophy']:
        messages.error(request, "You don't have permission to approve events.")
        return redirect('events')
    
    if request.method == 'POST':
        event_id = request.POST.get('event_id')
        
        try:
            # Update event status to approved
            result = Events.update_one(
                {'_id': ObjectId(event_id)},
                {
                    '$set': {
                        'status': 'approved',
                        'approved_by': name,
                        'approved_at': datetime.now(),
                        'updated_at': datetime.now()
                    }
                }
            )
            
            if result.modified_count > 0:
                messages.success(request, "Event has been approved successfully!")
            else:
                messages.error(request, "Event not found or already processed.")
                
        except Exception as e:
            logger.error(f"Error approving event: {e}")
            messages.error(request, "An error occurred while approving the event.")
    
    return redirect('events')

# Reject event view (admin only)
@csrf_exempt
def reject_event(request):
    if not request.session.get('user_id'):
        return redirect('login')
    
    userinfo(request)
    
    # Check if user is admin
    if name not in ['Faisal', 'Jophy']:
        messages.error(request, "You don't have permission to reject events.")
        return redirect('events')
    
    if request.method == 'POST':
        event_id = request.POST.get('event_id')
        
        try:
            # Update event status to rejected
            result = Events.update_one(
                {'_id': ObjectId(event_id)},
                {
                    '$set': {
                        'status': 'rejected',
                        'rejected_by': name,
                        'rejected_at': datetime.now(),
                        'updated_at': datetime.now()
                    }
                }
            )
            
            if result.modified_count > 0:
                # Optionally delete associated images
                EventImages.delete_many({'event_id': event_id})
                messages.success(request, "Event has been rejected.")
            else:
                messages.error(request, "Event not found or already processed.")
                
        except Exception as e:
            logger.error(f"Error rejecting event: {e}")
            messages.error(request, "An error occurred while rejecting the event.")
    
    return redirect('events')

# Get event details (for AJAX calls)
@csrf_exempt
def get_event_details(request, event_id):
    if not request.session.get('user_id'):
        return JsonResponse({'status': 'error', 'message': 'Not authenticated'}, status=401)
    
    try:
        event = Events.find_one({'_id': ObjectId(event_id)})
        
        if not event:
            return JsonResponse({'status': 'error', 'message': 'Event not found'}, status=404)
        
        # Get event images
        images = list(EventImages.find({'event_id': event_id}))
        image_urls = [img['image_url'] for img in images]
        
        event_data = {
            'id': str(event['_id']),
            'name': event.get('name', ''),
            'description': event.get('description', ''),
            'event_date': event.get('event_date', ''),
            'event_time': event.get('event_time', ''),
            'location': event.get('location', ''),
            'lat': event.get('lat'),
            'lon': event.get('lon'),
            'created_by': event.get('created_by', ''),
            'status': event.get('status', ''),
            'images': image_urls,
            'created_at': event.get('created_at', '').isoformat() if event.get('created_at') else ''
        }
        
        return JsonResponse({'status': 'success', 'event': event_data})
        
    except Exception as e:
        logger.error(f"Error getting event details: {e}")
        return JsonResponse({'status': 'error', 'message': 'Internal server error'}, status=500)
    
#---------------------------------------------------------------------------------------------------------------------
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

# Add these functions to your views.py - Event management functions
def cleanup_old_events():
    """Remove events older than 30 days from past events"""
    try:
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        # Find events that are older than 30 days
        old_events = Events.find({
            'event_date': {'$lt': thirty_days_ago.strftime('%Y-%m-%d')},
            'status': 'past'
        })
        
        deleted_count = 0
        for event in old_events:
            event_id = str(event['_id'])
            
            # Delete associated images from filesystem
            event_images = EventImages.find({'event_id': event_id})
            for img in event_images:
                try:
                    file_path = os.path.join(settings.MEDIA_ROOT, img['image_url'].lstrip('/media/'))
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    logger.error(f"Error deleting image file: {e}")
            
            # Delete from database
            EventImages.delete_many({'event_id': event_id})
            Events.delete_one({'_id': event['_id']})
            deleted_count += 1
        
        logger.info(f"Cleaned up {deleted_count} old events")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_events: {e}")
        return 0

def move_past_events():
    """Move events that have passed their date to past status"""
    try:
        today = datetime.now().date()
        
        # Find approved events that have passed their date
        past_events = Events.find({
            'status': 'approved',
            'event_date': {'$exists': True, '$ne': ''}
        })
        
        moved_count = 0
        for event in past_events:
            try:
                event_date_str = event.get('event_date', '')
                if event_date_str:
                    # Handle different date formats
                    try:
                        event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
                    except ValueError:
                        try:
                            event_date = datetime.strptime(event_date_str, '%m/%d/%Y').date()
                        except ValueError:
                            continue  # Skip if date format is not recognized
                    
                    # Check if event date has passed
                    if event_date < today:
                        # Update status to past
                        Events.update_one(
                            {'_id': event['_id']},
                            {
                                '$set': {
                                    'status': 'past',
                                    'moved_to_past_at': datetime.now()
                                }
                            }
                        )
                        moved_count += 1
                        
            except Exception as e:
                logger.error(f"Error processing event {event.get('_id')}: {e}")
                continue
        
        logger.info(f"Moved {moved_count} events to past status")
        return moved_count
        
    except Exception as e:
        logger.error(f"Error in move_past_events: {e}")
        return 0

# Updated events_view function
def events_view(request):
    if not request.session.get('user_id'):
        return redirect('login')
    
    userinfo(request)
    
    # Move old events to separate collection
    move_old_events()
    
    # Check if user is admin (Faisal or Jophy)
    is_admin = name in ['Faisal', 'Jophy']
    
    # Get current approved events (future events only)
    today = date.today().strftime('%Y-%m-%d')
    approved_events = list(Events.find({
        'status': 'approved',
        '$or': [
            {'event_date': {'$gte': today}},  # Future events
            {'event_date': {'$exists': False}},  # Events without date
            {'event_date': ""}  # Events with empty date
        ]
    }).sort('event_date', 1))  # Sort by date ascending
    
    # Get user's own current events
    user_events = list(Events.find({
        'created_by': name,
        '$or': [
            {'event_date': {'$gte': today}},  # Future events
            {'event_date': {'$exists': False}},  # Events without date
            {'event_date': ""}  # Events with empty date
        ]
    }).sort('created_at', -1))
    
    # Get pending events for admin
    pending_events = []
    if is_admin:
        pending_events = list(Events.find({'status': 'pending'}).sort('created_at', -1))
    
    # Get past events for the current user
    past_events = list(OldEvents.find({
        '$or': [
            {'created_by': name},  # Events created by user
            {'status': 'approved'}  # All approved past events (community events)
        ]
    }).sort('moved_at', -1))
    
    # Process events to add image URLs
    for event_list in [approved_events, user_events, pending_events, past_events]:
        for event in event_list:
            event['id'] = str(event.get('_id', event.get('original_id', '')))
            # Get first image for display
            event_id = str(event.get('_id', event.get('original_id', '')))
            event_images = EventImages.find({'event_id': event_id}).limit(1)
            first_image = next(event_images, None)
            event['image'] = first_image['image_url'] if first_image else None
    
    context = {
        'approved_events': approved_events,
        'user_events': user_events,
        'pending_events': pending_events,
        'past_events': past_events,  # Add past events to context
        'is_admin': is_admin,
        'name': name
    }
    
    return render(request, 'MainApp/events.html', context)


@csrf_exempt
def get_notification_counts(request):
    """
    Get current notification counts for the user
    """
    if not request.session.get('user_id'):
        return JsonResponse({'status': 'error', 'message': 'Not authenticated'}, status=401)
    
    userinfo(request)
    
    try:
        # Get current notification counts
        friend_request_count = FriendReq.find({"To": name}).count()
        date_request_count = DateReq.find({"To": name, "status": "pending"}).count()
        
        return JsonResponse({
            'status': 'success',
            'friend_count': friend_request_count,
            'date_count': date_request_count
        })
        
    except Exception as e:
        logger.error(f"Error getting notification counts: {e}")
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to get notification counts'
        }, status=500)


# Also add this to clear notifications when user views them
@csrf_exempt
def mark_notifications_seen(request):
    """
    Mark notifications as seen (optional - for future use)
    """
    if not request.session.get('user_id'):
        return JsonResponse({'status': 'error', 'message': 'Not authenticated'}, status=401)
    
    userinfo(request)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
            notification_type = data.get('type')  # 'friend' or 'date'
            
            # You can implement logic here to mark specific notifications as seen
            # For now, we'll just return success
            
            return JsonResponse({
                'status': 'success',
                'message': f'{notification_type} notifications marked as seen'
            })
            
        except Exception as e:
            logger.error(f"Error marking notifications as seen: {e}")
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to mark notifications as seen'
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Only POST method allowed'
    }, status=405)
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from bson.objectid import ObjectId
from pymongo import MongoClient
from django.http import JsonResponse
from passlib.hash import pbkdf2_sha256  # For password hashing

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['UserDetails']
users_collection = db['AccountHashing']
FriendReq = db['Friendrequest']
Friendlist = db['FriendList']

def userinfo(request):
    global user
    user = request.session.get('user_id')  # getting The userid of the account first
    global name
    name = users_collection.find_one({"_id": ObjectId(user)}).get('username')  # extracts username
def home(request):
    # Redirect to area_view if user is logged in
    if not request.session.get('user_id'):
        return render(request, 'MainApp/login.html')
    return render(request, 'MainApp/area.html')


def login_view(request):#to login
    if request.session.get('user_id'):  # If already logged in, redirect to area_view
        return render(request, 'MainApp/area.html')

    if request.method == 'POST':#gets username and password for authentication
        username = request.POST['username']
        password = request.POST['password']

        user = users_collection.find_one({"username": username})

        if user and pbkdf2_sha256.verify(password, user['password']): #encrypts data
            # Store the user ID in the session
            request.session['user_id'] = str(user['_id'])
            request.session['login_success'] = True  # Set login success flag
            return redirect('area')
        else:
            messages.error(request, "Invalid username or password")
    return render(request, 'MainApp/login.html')

def signup_view(request):
    if request.session.get('user_id'):  # If already logged in, redirect to area_view
        return redirect('area_view')

    if request.method == 'POST':#takes the username password email for signup
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password == confirm_password:#confirm if password is correct
            if users_collection.find_one({"username": username}): #searches if username exists or not
                messages.error(request, "Username already exists")
            elif users_collection.find_one({"email": email}):#
                messages.error(request, "Email already registered")
            else:
                hashed_password = pbkdf2_sha256.hash(password)
                new_user = {
                    "username": username,
                    "email": email,
                    "password": hashed_password  # Saving the hashed password
                }
                users_collection.insert_one(new_user)  # Insert user into MongoDB
                # Set session variable to show success message
                request.session['user_id'] = str(new_user['_id'])
                request.session['account_created'] = True  # Set account created flag
                return redirect('area')
        else:
            messages.error(request, "Passwords do not match")
    return render(request, 'MainApp/signup.html')

def area_view(request):#Main page that shows upcoming dates and popular events
    if not request.session.get('user_id'):  # Ensure user is logged in
        return redirect('login')
    
    # Check if account was just created and delete the session key
    account_created = request.session.get('account_created', False)
    login_success = request.session.get('login_success', False)
    
    if 'account_created' in request.session:
        del request.session['account_created']  # Explicitly delete it after checking
    
    if 'login_success' in request.session:
        del request.session['login_success']  # Explicitly delete it after checking

    return render(request, 'MainApp/area.html', {'account_created': account_created, 'login_success': login_success})

def logout_view(request):
    if 'user_id' in request.session:
        del request.session['user_id']  # Remove user ID from session
    return redirect('login')  # Redirect to login page after logout

# Search user and send a friend request if the user exists
def search_user(request):
    userinfo(request)

    # Get pending friend requests for the current user
    friends = []
    friend_requests = FriendReq.find({"To": name})  # Find all friend requests sent to the current user
    for friend in friend_requests:
        friends.append(friend["From"])

    if request.method == "POST":#retrieves username
        username = request.POST.get('username')
        if not username:#checks if it is empty
            messages.error(request, "No username provided.")

            return render(request, 'MainApp/area.html')
        
        try:
            userinfo(request)#gets the detail of logged in user
            user = users_collection.find_one({"username":username})  # Finds a specific username
            if user:#checks if isnt empty
                    if username==name:#checks if he is trying to friend himself
                        return redirect("search_user")
                    userfriendlist=Friendlist.find_one({"username":name})
                    for i in userfriendlist['friends']:#checks if the user is already in friendlist
                        if i==username:
                            return redirect("search_user")
                    friend={
                        "From":name,
                        "To":username
                    }
                    FriendReq.insert_one(friend)
                    return redirect("area")
        except username.DoesNotExist:
            messages.error(request, "Invalid username.")
            return redirect("area")
    return render(request, 'MainApp/search.html')


def check_request(request):
    userinfo(request)  # Ensure user is logged in and `name` is set
    pending_requests = FriendReq.find({"To": name})  # Get all friend requests to the current user
    friends = []  # List to hold the usernames of users who sent requests
    for request in pending_requests:
        friends.append(request["From"])  # Add the sender's username to the friends list
    return render(request, "MainApp/.html", {"friends": friends})  # Pass friends to the template

def accept_request(request):
    userinfo(request)  #  this function retrieves and sets `name` (current user's name)

    if request.method == "POST":
        friendname = request.POST.get('friend_id')  # Get the friend Name from the form
        friend_request = FriendReq.find_one({"From": friendname, "To": name})
        if friend_request:
            sender = friend_request["From"]  # The user who sent the friend request
            receiver = name  # The current user accepting the request
            # Update the sender's friend list
            Friendlist.update_one(
                {"username": sender},
                {"$addToSet": {"friends": receiver}},
                upsert=True  # Create document if it doesn't exist
            )

            # Update the receiver's friend list
            Friendlist.update_one(
                {"username": receiver},
                {"$addToSet": {"friends": sender}},
                upsert=True  # Create document if it doesn't exist
            )
    FriendReq.delete_one({"From": friendname,"To":name}) 
    return redirect("friendreq")


def reject_request(request):
    if request.method == "POST":
        friendname = request.POST.get('friend_id')  # Get the friend request ID from the form
        FriendReq.delete_one({"From": friendname, "To": name})
        messages.success(request, f"Friend request from {friendname} rejected!")
    return redirect("search_user")

def profile(request):
    return render(request, 'MainApp/profile.html')




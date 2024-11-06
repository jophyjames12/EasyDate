from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from bson.objectid import ObjectId
from pymongo import MongoClient
from passlib.hash import pbkdf2_sha256  # For password hashing
#from .models import FriendRequest, FriendList
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['UserDetails'] 
users_collection = db['AccountHashing']  
FriendReq=db['Friendrequest']

def userinfo(request):
    global user
    user=request.session.get('user_id') #getting The userid of the account first
    global name
    name=users_collection.find_one({"_id":ObjectId(user)}).get('username') #extracts username
    
#commenting delete if found laterrr
def home(request):
    # Redirect to area_view if user is logged in
    if not request.session.get('user_id'):
        return render(request,'MainApp/login.html')
    return render(request, 'MainApp/area.html')


def login_view(request):
    if request.session.get('user_id'):  # If already logged in, redirect to area_view
        return render(request,'MainApp/area.html')

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = users_collection.find_one({"username": username})

        if user and pbkdf2_sha256.verify(password, user['password']):
            # Store the user ID in the session
            request.session['user_id'] = str(user['_id'])
            return redirect('area')
        else:
            messages.error(request, "Invalid username or password")
    return render(request, 'MainApp/login.html')

def signup_view(request):
    if request.session.get('user_id'):  # If already logged in, redirect to area_view
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
                    "password": hashed_password  # Saving the hashed password
                }
                users_collection.insert_one(new_user)  # Insert user into MongoDB
                messages.success(request, "Account created successfully!")
                return redirect('login')
        else:
            messages.error(request, "Passwords do not match")
    return render(request, 'MainApp/signup.html')

def area_view(request):
    if not request.session.get('user_id'):  # Ensure user is logged in
        return redirect('login')
    return render(request, 'MainApp/area.html')

def logout_view(request):
    if 'user_id' in request.session:
        del request.session['user_id']  # Remove user ID from session
    return redirect('login')  # Redirect to login page after logout

# Search user and send a friend request if the user exists
def search_user(request):

    if request.method == "POST":
        username = request.POST.get('username')
        if not username:
            messages.error(request, "No username provided.")
            return render(request, 'MainApp/search.html')
        
        try:
            userinfo(request)
            all_users = users_collection.find()  # Fetches all documents in the collection
            for user in all_users:
                if user['username']==username:
                    friend={
                        "From":name,
                        "To":username
                    }
                    FriendReq.insert_one(friend)
                    
                    return render(request, 'MainApp/user_found.html', {'user': user})
        except username.DoesNotExist:
            messages.error(request, "Invalid username.")
            return render(request, 'MainApp/search.html')
    return render(request, 'MainApp/search.html')
def check_request(request):
    userinfo(request)
    friends=[]
    friend_list=FriendReq.find()
    for friend in friend_list:
        if friend["To"]==name:
            friend_id = friend["_id"]
            friends.append(friend_id)
    return render(request, "MainApp/friend_requests.html", {"friends": friends})
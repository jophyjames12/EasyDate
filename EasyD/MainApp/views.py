from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from bson.objectid import ObjectId
from pymongo import MongoClient
from passlib.hash import pbkdf2_sha256  # For password hashing

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['UserDetails']
users_collection = db['AccountHashing']
FriendReq = db['Friendrequest']
Friendlist = db['FriendList']

def userinfo(request):
    global user
    user = request.session.get('user_id')
    global name
    name = users_collection.find_one({"_id": ObjectId(user)}).get('username')

def home(request):
    if not request.session.get('user_id'):
        return render(request, 'MainApp/login.html')
    return render(request, 'MainApp/area.html')

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

def logout_view(request):
    if 'user_id' in request.session:
        del request.session['user_id']
    return redirect('login')

def search_user(request):
    userinfo(request)
    if request.method == "POST":
        username = request.POST.get('username')
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
            
            friend_request = {
                "From": name,
                "To": username
            }
            FriendReq.insert_one(friend_request)
            messages.success(request, f"Friend request sent to {username}.")
            return redirect("search_user")
        
        messages.error(request, "User not found.")
        return redirect("search_user")
    
    # Retrieve pending friend requests and all friends for the logged-in user
    friends = []
    friend_requests = FriendReq.find({"To": name})
    for friend in friend_requests:
        friends.append(friend["From"])

    # Retrieve current user's friends list
    user_friendlist = Friendlist.find_one({"username": name})
    all_friends = user_friendlist.get("friends", []) if user_friendlist else []

    return render(request, "MainApp/search.html", {"friends": friends, "all_friends": all_friends})

def check_request(request):
    userinfo(request)
    pending_requests = FriendReq.find({"To": name})
    friends = []
    for friend_request in pending_requests:
        friends.append(friend_request["From"])
    return render(request, "MainApp/search.html", {"friends": friends})

def accept_request(request):
    userinfo(request)

    if request.method == "POST":
        friendname = request.POST.get('friend_id')
        friend_request = FriendReq.find_one({"From": friendname, "To": name})
        if friend_request:
            sender = friend_request["From"]
            receiver = name
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
            FriendReq.delete_one({"From": friendname, "To": name})
            messages.success(request, f"You are now friends with {friendname}.")
    return redirect("search_user")

def reject_request(request):
    if request.method == "POST":
        friendname = request.POST.get('friend_id')
        FriendReq.delete_one({"From": friendname, "To": name})
        messages.success(request, f"Friend request from {friendname} rejected!")
    return redirect("search_user")

def profile(request):
    return render(request, 'MainApp/profile.html')






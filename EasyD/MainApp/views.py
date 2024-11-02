from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from pymongo import MongoClient
from passlib.hash import pbkdf2_sha256  # For password hashing

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['UserDetails']  # Use your actual database name
users_collection = db['AccountHashing']  # Use your actual collection name

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = users_collection.find_one({"username": username})

        if user and pbkdf2_sha256.verify(password, user['password']):
            # Store the user ID in the session
            request.session['user_id'] = str(user['_id'])
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password")
    return render(request, 'MainApp/login.html')

def signup_view(request):
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
    return render(request, 'MainApp/area.html')


def logout_view(request):
    logout(request)
    return redirect('login')  # Redirect to login page after logout

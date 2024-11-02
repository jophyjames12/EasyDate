from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages


# Create your views here.
def home(request):
    return render(request, 'MainApp/home.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')  # Update this to the URL you want to redirect to after login
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
            if User.objects.filter(username=username).exists():
                messages.error(request, "Username already exists")
            elif User.objects.filter(email=email).exists():
                messages.error(request, "Email already registered")
            else:
                user = User.objects.create_user(username=username, email=email, password=password)
                user.save()
                login(request, user)
                return redirect('home')  # Update this to the URL you want to redirect to after signup
        else:
            messages.error(request, "Passwords do not match")
    return render(request, 'MainApp/signup.html')

def area_view(request):
    return render(request, 'MainApp/area.html')


def logout_view(request):
    logout(request)
    return redirect('login')  # Redirect to login page after logout
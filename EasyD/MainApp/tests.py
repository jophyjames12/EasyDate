from django.test import TestCase
from pymongo import MongoClient
client = MongoClient('mongodb://localhost:27017/')
db = client['UserDetails'] 
users_collection = db['AccountHashing'] 

all_users = users_collection.find()  # Fetches all documents in the collection
for user in all_users:
    print(user)  # Print each user document



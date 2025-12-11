
import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

def list_chats():
    mongo_uri = os.getenv("MONGODB_URI")
    client = MongoClient(mongo_uri)
    db = client[os.getenv("MONGODB_DATABASE", "docurag")]
    
    chats = list(db.chats.find().limit(10))
    print(f"Total Chats: {db.chats.count_documents({})}")
    for c in chats:
        print(f"ID: {c['id']}, Title: {c.get('title')}, Project: {c.get('project_id')}")

if __name__ == "__main__":
    list_chats()

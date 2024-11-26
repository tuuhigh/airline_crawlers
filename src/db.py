import datetime
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson.objectid import ObjectId
from src.constants import MONGODB_NAME, MONGODB_URL

def get_multilogin_profile() -> dict[str, dict]:
    client = MongoClient(MONGODB_URL)
    db = client[MONGODB_NAME]
    multilogin_browsers = db['multilogin_browsers']
    utc_now = datetime.datetime.utcnow()

    query = {}
    sort = [('last_used', ASCENDING), ('_id', ASCENDING)]
    update = {
        "$set": {
            "last_used": utc_now
        }
    }

    profile = multilogin_browsers.find_one_and_update(query, update, sort=sort)

    client.close()
    return profile

def get_multilogin_profile_blocked_webrtc() -> dict[str, dict]:
    client = MongoClient(MONGODB_URL)
    db = client[MONGODB_NAME]
    multilogin_browsers = db['multilogin_browsers_blocked_webrtc']
    utc_now = datetime.datetime.utcnow()

    query = {}
    sort = [('last_used', ASCENDING), ('_id', ASCENDING)]
    update = {
        "$set": {
            "last_used": utc_now
        }
    }

    profile = multilogin_browsers.find_one_and_update(query, update, sort=sort)

    client.close()
    return profile

def insert_target_headers(headers, target_name, payload={}):
    """
    """
    client = MongoClient(MONGODB_URL)
    db = client[MONGODB_NAME]
    delta_headers = db[f'{target_name}_headers']
    utc_now = datetime.datetime.utcnow()

    values = {
        "headers": headers,
        "payload": payload,
        "active": True,
        "created_at": utc_now
    }

    rec = delta_headers.insert_one(values)

    client.close()
    return rec

def get_target_headers(target_name):
    client = MongoClient(MONGODB_URL)
    db = client[MONGODB_NAME]
    delta_headers = db[f'{target_name}_headers']
    utc_now = datetime.datetime.utcnow()
    query = {'_id': ObjectId('66b266116e52a82ee187e813')}

    query = {'active': True}
    sort = [('created_at', DESCENDING), ('_id', ASCENDING)]

    active_headers = list(delta_headers.find(query, sort=sort))

    client.close()
    return active_headers

def update_target_headers(rec_id, vals, target_name):
    client = MongoClient(MONGODB_URL)
    db = client[MONGODB_NAME]
    delta_headers = db[f'{target_name}_headers']
    utc_now = datetime.datetime.utcnow()

    query = {
        "_id": rec_id
    }
    update = {
        "$set": vals
    }

    res = delta_headers.update_one(query, update)

    client.close()
    return res
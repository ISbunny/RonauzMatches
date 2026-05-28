from pymongo import MongoClient

SINGLE_ACCOUNT_GUARD_FIELD = "single_account_guard"

_client = None
_db_name = "ronauz_matches"
_indexes_ready = False
_single_account_bootstrapped = False


def init_mongo(app):
    global _client
    uri = app.config["MONGODB_URI"]
    _client = MongoClient(uri, serverSelectionTimeoutMS=3000, connect=False)


def get_users_collection():
    global _indexes_ready, _single_account_bootstrapped

    if _client is None:
        raise RuntimeError("Mongo client is not initialized")

    mongo_db = _client.get_default_database()
    if mongo_db is None:
        mongo_db = _client[_db_name]

    users = mongo_db["users"]

    if not _indexes_ready:
        users.create_index("username", unique=True)
        users.create_index(
            SINGLE_ACCOUNT_GUARD_FIELD,
            unique=True,
            partialFilterExpression={SINGLE_ACCOUNT_GUARD_FIELD: True},
        )
        _indexes_ready = True

    if not _single_account_bootstrapped:
        if users.count_documents({SINGLE_ACCOUNT_GUARD_FIELD: True}) == 0:
            first_user = users.find_one({}, {"_id": 1})
            if first_user:
                users.update_one(
                    {"_id": first_user["_id"]},
                    {"$set": {SINGLE_ACCOUNT_GUARD_FIELD: True}},
                )
        _single_account_bootstrapped = True

    return users

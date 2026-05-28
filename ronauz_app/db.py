from pymongo import MongoClient

SINGLE_ACCOUNT_GUARD_FIELD = "single_account_guard"

_client = None
_db_name = "ronauz_matches"
_user_indexes_ready = False
_match_odds_indexes_ready = False
_single_account_bootstrapped = False


def init_mongo(app):
    global _client
    uri = app.config["MONGODB_URI"]
    _client = MongoClient(uri, serverSelectionTimeoutMS=3000, connect=False)


def get_database():
    if _client is None:
        raise RuntimeError("Mongo client is not initialized")

    mongo_db = _client.get_default_database()
    if mongo_db is None:
        mongo_db = _client[_db_name]

    return mongo_db


def get_users_collection():
    global _user_indexes_ready, _single_account_bootstrapped

    users = get_database()["users"]

    if not _user_indexes_ready:
        users.create_index("username", unique=True)
        users.create_index(
            SINGLE_ACCOUNT_GUARD_FIELD,
            unique=True,
            partialFilterExpression={SINGLE_ACCOUNT_GUARD_FIELD: True},
        )
        _user_indexes_ready = True

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


def get_match_odds_collection():
    global _match_odds_indexes_ready

    collection = get_database()["match_odds"]

    if not _match_odds_indexes_ready:
        collection.create_index("match_key", unique=True)
        collection.create_index("tournament_key")
        collection.create_index("last_fetched_at")
        _match_odds_indexes_ready = True

    return collection

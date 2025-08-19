# This file manages the user's current state, for features like search.
# A simple dictionary is used as an in-memory state machine.
# {user_id: {'state': 'searching_country', 'context': {...}} }

USER_STATE = {}

def set_user_state(user_id, state, context=None):
    """Sets the state for a given user."""
    if context is None:
        context = {}
    USER_STATE[user_id] = {'state': state, 'context': context}

def get_user_state(user_id):
    """Gets the state for a given user."""
    return USER_STATE.get(user_id)

def clear_user_state(user_id):
    """Clears the state for a given user."""
    if user_id in USER_STATE:
        del USER_STATE[user_id]

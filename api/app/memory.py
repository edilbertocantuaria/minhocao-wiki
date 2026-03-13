memory_store = {}

def get_history(session_id):

    return memory_store.get(session_id, [])


def save_message(session_id, role, content):

    if session_id not in memory_store:
        memory_store[session_id] = []

    memory_store[session_id].append(
        {
            "role": role,
            "content": content
        }
    )

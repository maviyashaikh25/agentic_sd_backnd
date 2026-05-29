from collections import deque


class ShortTermMemory:

    def __init__(self, max_messages=10):

        self.messages = deque(maxlen=max_messages)

    def add_message(self, role, content):

        self.messages.append({
            "role": role,
            "content": content
        })

    def get_messages(self):

        return list(self.messages)

    def clear(self):

        self.messages.clear()
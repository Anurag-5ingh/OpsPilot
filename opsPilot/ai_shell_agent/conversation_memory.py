# conversation_memory.py

class ConversationMemory:
    def __init__(self, max_entries=20):
        self.max_entries = max_entries
        self.history = []

    def add(self, user_prompt: str, ai_response: str):
        entry = (user_prompt, ai_response)
        self.history.append(entry)

        if len(self.history) > self.max_entries:
            removed = self.history.pop(0)
            print(f"Removed oldest memory entry: {removed[0][:60]}...")

        print(f"Memory updated. Total interactions: {len(self.history)}")

    def get(self):
        return self.history

    def clear(self):
        self.history = []
        print("Memory cleared.")

    def print_summary(self):
        print("Memory Summary:")
        for i, (user, ai) in enumerate(self.history, 1):
            print(f"{i}. User: {user[:50]} | AI: {ai[:50]}")

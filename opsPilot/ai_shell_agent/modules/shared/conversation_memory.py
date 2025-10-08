"""
Conversation Memory
Stores conversation history for context-aware AI responses
"""


class ConversationMemory:
    """Manages conversation history with automatic cleanup."""
    
    def __init__(self, max_entries=20):
        """
        Initialize conversation memory.
        
        Args:
            max_entries: Maximum number of conversation entries to keep
        """
        self.max_entries = max_entries
        self.history = []

    def add(self, user_prompt: str, ai_response: str):
        """
        Add a conversation entry.
        
        Args:
            user_prompt: User's input
            ai_response: AI's response
        """
        entry = (user_prompt, ai_response)
        self.history.append(entry)

        if len(self.history) > self.max_entries:
            removed = self.history.pop(0)
            print(f"Removed oldest memory entry: {removed[0][:60]}...")

        print(f"Memory updated. Total interactions: {len(self.history)}")

    def get(self):
        """Get all conversation history."""
        return self.history

    def clear(self):
        """Clear all conversation history."""
        self.history = []
        print("Memory cleared.")

    def print_summary(self):
        """Print a summary of conversation history."""
        print("Memory Summary:")
        for i, (user, ai) in enumerate(self.history, 1):
            print(f"{i}. User: {user[:50]} | AI: {ai[:50]}")

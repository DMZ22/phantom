import logging
import anthropic
from django.conf import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are Phantom, a charismatic movie expert AI. You know everything about movies. "
    "You speak casually like a film-buff friend. When discussing a specific movie, provide "
    "insights about plot, themes, hidden details, similar movies, and fun trivia. Keep "
    "responses concise (2-3 paragraphs max). Be entertaining and passionate about cinema."
)


class ChatService:
    def __init__(self):
        self.client = None

    def _ensure_init(self):
        if not self.client:
            key = getattr(settings, 'ANTHROPIC_API_KEY', '')
            self.client = anthropic.Anthropic(api_key=key)

    def chat(self, movie_id, movie_title, movie_overview, messages):
        self._ensure_init()
        system = SYSTEM_PROMPT
        if movie_title:
            system += f"\n\nCurrently discussing: '{movie_title}' (ID: {movie_id}). Overview: {movie_overview or 'N/A'}"

        api_msgs = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m.get("role") in ("user", "assistant")
        ]
        if not api_msgs or api_msgs[0]["role"] != "user":
            api_msgs.insert(0, {"role": "user", "content": "Tell me about this movie!"})

        try:
            r = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=system,
                messages=api_msgs,
            )
            return r.content[0].text
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return "My projector bulb blew out! Try again in a moment."


chat_service = ChatService()

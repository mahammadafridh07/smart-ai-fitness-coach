class TextToSpeech:
    def __init__(self, groq_client):
        self.groq_client = groq_client

    def speak(self, text, lang="en"):
        cleaned = (text or "").strip()

        if not cleaned:
            return None

        try:
            cleaned = cleaned[:200]

            response = self.groq_client.audio.speech.create(
                model="canopylabs/orpheus-v1-english",
                voice="troy",
                input=cleaned,
                response_format="wav"
            )

            return response.read()

        except Exception as e:
            print("TTS ERROR:", e)
            return None
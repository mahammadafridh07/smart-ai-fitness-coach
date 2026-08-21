from io import BytesIO
from gtts import gTTS


class TextToSpeech:

    def speak(self, text, lang="en"):
        cleaned = (text or "").strip()

        if not cleaned:
            return None

        try:
            buffer = BytesIO()

            tts = gTTS(
                text=cleaned,
                lang=lang,
                slow=False
            )

            tts.write_to_fp(buffer)

            buffer.seek(0)

            return buffer.read()

        except Exception as e:
            print("TTS error:", e)
            return None
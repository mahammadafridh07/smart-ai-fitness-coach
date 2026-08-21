from services.config.workout_config import PROMPT


class LLMCoach:

    def __init__(self, groq_client):
        self.client = groq_client
        self.history = []
        self.system_prompt = PROMPT

    def give_feedback(self, event, issue):

        prompt = f"Event: {event}"

        if issue:
            prompt += f" Form Issue: {issue}"

        messages = [
            {
                "role": "system",
                "content": self.system_prompt
            },
            *self.history[-10:],
            {
                "role": "user",
                "content": prompt
            }
        ]

        try:
            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                temperature=0.4,
                max_completion_tokens=256
            )

            text = response.choices[0].message.content

            if not text:
                return "Keep going! Stay focused on your form."

            text = text.strip()

            self.history.append(
                {
                    "role": "assistant",
                    "content": text
                }
            )

            return text

        except Exception as e:
            print("=" * 60)
            print("GROQ API ERROR")
            print("=" * 60)
            print("Error type:", type(e).__name__)
            print("Error:", str(e))
            print("=" * 60)

            return (
                "I'm having trouble connecting to "
                "the AI coach right now. "
                "Please continue your workout."
            )
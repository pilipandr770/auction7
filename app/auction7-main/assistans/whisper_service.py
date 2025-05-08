import openai
import os

def transcribe(audio_file):
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file
    )
    return transcript.text

import openai
import os
import uuid

def synthesize(text):
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    speech = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text
    )
    filename = f"assistans/static/audio/{uuid.uuid4()}.mp3"
    speech.stream_to_file(filename)
    return filename

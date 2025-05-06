from flask import Blueprint, request, jsonify
import os
from openai import OpenAI
from .tts_service import synthesize
from .whisper_service import transcribe
import logging

logger = logging.getLogger("assistant")
logger.setLevel(logging.INFO)
handler = logging.FileHandler("assistant.log", encoding="utf-8")
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(handler)

assistant_bp = Blueprint('assistant_bp', __name__, url_prefix='/assistans')

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")

@assistant_bp.route('/ask', methods=['POST'])
def ask():
    data = request.json
    message = data.get("message")
    logger.info(f"[USER] {message}")
    if not message:
        logger.error("Пусте повідомлення")
        return jsonify({"error": "Пусте повідомлення"}), 400
    try:
        thread = client.beta.threads.create()
        logger.info(f"[THREAD] created: {thread.id}")
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=message
        )
        logger.info(f"[THREAD] message sent: {message}")
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )
        logger.info(f"[RUN] started: {run.id}")
        import time
        while True:
            run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            logger.info(f"[RUN] status: {run_status.status}")
            if run_status.status in ["completed", "failed", "cancelled"]:
                break
            time.sleep(1)
        if run_status.status != "completed":
            logger.error(f"[RUN] not completed: {run_status.status}")
            return jsonify({"error": "Асистент не відповів"}), 500
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        logger.info(f"[MESSAGES] count: {len(messages.data)}")
        # Вибираємо першу відповідь асистента
        reply = next((m.content[0].text.value for m in messages.data if m.role == "assistant"), "Вибачте, не вдалося отримати відповідь.")
        logger.info(f"[ASSISTANT] {reply}")
        audio_path = synthesize(reply)
        logger.info(f"[AUDIO] {audio_path}")
        # Зберігаємо mp3 у app/static/audio
        import shutil, os
        from pathlib import Path
        audio_dir = Path('app/static/audio')
        audio_dir.mkdir(parents=True, exist_ok=True)
        new_audio_path = audio_dir / os.path.basename(audio_path)
        shutil.move(audio_path, new_audio_path)
        return jsonify({"response": reply, "audio": f"/static/audio/{new_audio_path.name}"})
    except Exception as e:
        logger.exception(f"[ERROR] {str(e)}")
        return jsonify({"error": str(e)}), 500

@assistant_bp.route('/whisper', methods=['POST'])
def whisper():
    if 'audio' not in request.files:
        return jsonify({'error': 'Немає аудіофайлу'}), 400
    audio_file = request.files['audio']
    text = transcribe(audio_file)
    return jsonify({'text': text})

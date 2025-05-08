
let mediaRecorder;
let audioChunks = [];
let chatVisible = false;

const voiceButton = document.getElementById("voice-button");
const chatBox = document.getElementById("assistant-chat");
const chatLog = document.getElementById("chat-log");
const chatInput = document.getElementById("chat-input");
const chatSend = document.getElementById("chat-send");

voiceButton.addEventListener("mousedown", startRecording);
voiceButton.addEventListener("mouseup", stopRecording);
voiceButton.addEventListener("touchstart", startRecording);
voiceButton.addEventListener("touchend", stopRecording);

chatSend.addEventListener("click", sendText);

function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.start();
        audioChunks = [];

        mediaRecorder.addEventListener("dataavailable", event => {
            audioChunks.push(event.data);
        });

        voiceButton.style.backgroundColor = "red";
    });
}

function stopRecording() {
    mediaRecorder.stop();
    voiceButton.style.backgroundColor = "";

    mediaRecorder.addEventListener("stop", () => {
        const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
        const formData = new FormData();
        formData.append("audio", audioBlob, "recording.wav");

        fetch("/assistant/whisper", { method: "POST", body: formData })
            .then(response => response.json())
            .then(data => {
                showChat();
                appendMessage("Ви", data.text);
                sendToAssistant(data.text);
            });
    });
}

function sendToAssistant(text) {
    fetch("/assistant/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text })
    })
    .then(response => response.json())
    .then(data => {
        appendMessage("Асистент", data.response);
        if (data.audio) {
            const audio = new Audio(data.audio);
            audio.play();
        }
    });
}

function sendText() {
    const text = chatInput.value;
    if (!text) return;
    appendMessage("Ви", text);
    chatInput.value = "";
    sendToAssistant(text);
}

function appendMessage(sender, message) {
    const el = document.createElement("div");
    el.innerHTML = `<strong>${sender}:</strong> ${message}`;
    chatLog.appendChild(el);
    chatLog.scrollTop = chatLog.scrollHeight;
}

function showChat() {
    if (!chatVisible) {
        chatBox.style.display = "block";
        chatVisible = true;
    }
}

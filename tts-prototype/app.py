from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
import pyttsx3
import tempfile
import base64

app = Flask(__name__)
socketio = SocketIO(app)

@app.route('/')
def index():
    with open('index.html') as f:
        return render_template_string(f.read())

@socketio.on('tts_request')
def handle_tts_request(data):
    text = data['text']
    engine = pyttsx3.init()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    engine.save_to_file(text, tmp.name)
    engine.runAndWait()
    with open(tmp.name, "rb") as f:
        audio_data = f.read()
    audio_b64 = base64.b64encode(audio_data).decode('utf-8')
    emit('tts_response', {'audio': audio_b64})

if __name__ == '__main__':
    socketio.run(app, debug=True)
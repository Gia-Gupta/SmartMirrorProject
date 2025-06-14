from flask import Flask, request, send_file, render_template_string
import pyttsx3
import tempfile

app = Flask(__name__)

@app.route('/')
def index():
    with open('index.html') as f:
        return render_template_string(f.read())

@app.route('/api/tts', methods=['POST'])
def tts_api():
    text = request.json['text']
    engine = pyttsx3.init()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    engine.save_to_file(text, tmp.name)
    engine.runAndWait()
    return send_file(tmp.name, mimetype='audio/mpeg')

if __name__ == '__main__':
    app.run(debug=True)
from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
import os

app = Flask(__name__)

# Gemini API Key 
genai.configure(api_key="AIzaSyC2f4tvcZM3fSNCso4hMd5ELBrTymw_gFI")
model = genai.GenerativeModel('gemini-pro')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message')
    # Yahan tumhara Gemini AI ka logic hona chahiye
    # ...
    return jsonify({'reply': "AI ka response yahan aayega"})
if __name__ == "__main__":
    import os
    # Cloud Run hamesha 'PORT' environment variable khud bhejta hai
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

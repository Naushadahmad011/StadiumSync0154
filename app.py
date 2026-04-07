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
    user_msg = request.json.get("message")
    
    # AI ko context dena
    context = """You are StadiMate, a helpful AI assistant for a large cricket stadium. 
    Stadium details: Block A, B, C are near Gate 1. Block D, E, F are near Gate 2. 
    Food stalls are near Gate 1 and Gate 3. Answer the user's query politely and shortly."""
    
    prompt = f"{context}\nUser: {user_msg}\nStadiMate:"
    
    try:
        response = model.generate_content(prompt)
        return jsonify({"reply": response.text})
    except Exception as e:
        return jsonify({"reply": "Sorry, I am facing a network issue right now."})

if __name__ == "__main__":
    import os
    # Cloud Run hamesha 'PORT' environment variable khud bhejta hai
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

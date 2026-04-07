from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
import os

app = Flask(__name__)

# Gemini API Key configuration
genai.configure(api_key="AIzaSyBH24DZBwEToD2vbA-OZU9f0H3E7l8BpNU")
model = genai.GenerativeModel('gemini-pro')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message')
        
        if not user_message:
            return jsonify({'reply': "Please type something!"}), 400

        # Gemini AI ko user ka message bhejna aur response lena
        response = model.generate_content(user_message)
        ai_reply = response.text
        
        return jsonify({'reply': ai_reply})
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'reply': "Sorry, I am facing a network issue right now."}), 500

if __name__ == "__main__":
    # Cloud Run hamesha 'PORT' environment variable khud bhejta hai
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

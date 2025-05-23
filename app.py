from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import openai
import os

app = Flask(__name__)

# ✅ OpenAI key (set in Render environment variables)
openai.api_key = os.getenv("OPENAI_API_KEY")

# 🧠 Per-user in-memory store
users = {}

# 📋 Onboarding fields
questions = [
    ("age", "🎂 What's your age?"),
    ("weight", "⚖️ What's your weight in kg?"),
    ("goal", "🎯 What's your primary fitness goal (e.g., lose fat, gain muscle)?"),
    ("diet", "🥗 Any dietary preference (e.g., vegetarian, keto)?")
]

# 🧠 GPT prompt template
def generate_prompt(user_data):
    return f"""
You are a world-class fitness coach and dietician helping a new client.

Client:
- Age: {user_data['age']}
- Weight: {user_data['weight']}
- Goal: {user_data['goal']}
- Diet: {user_data['diet']}

Create a powerful 5-day workout plan with sets, reps, and rest days. Include YouTube links for guidance. 
Then create a full-day meal plan tailored to their diet.

Make it motivational, engaging, and very practical. Use emojis and clear section headers.
"""

# 🤖 GPT response
def get_plan(user_data):
    prompt = generate_prompt(user_data)
    res = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an elite AI fitness and wellness assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    return res.choices[0].message.content.strip()

# 🔄 Main WhatsApp webhook
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.form.get("Body").strip()
    user_id = request.form.get("From")  # phone number
    response = MessagingResponse()
    msg = response.message()

    if user_id not in users:
        users[user_id] = {"step": 0, "data": {}, "complete": False}
        msg.body("💪 Welcome to *VitalAI* — your AI-powered personal coach.\nLet's get started! " + questions[0][1])
        return str(response)

    user = users[user_id]

    if incoming_msg.lower() == "restart":
        users[user_id] = {"step": 0, "data": {}, "complete": False}
        msg.body("🔄 Restarting setup. " + questions[0][1])
        return str(response)

    if user["complete"]:
        msg.body("✅ You're already onboarded!\nReply *restart* to reset or *plan* to view your plan again.")
        if incoming_msg.lower() == "plan":
            try:
                plan = get_plan(user["data"])
                msg.body(plan[:1600])  # WhatsApp max message size
            except Exception as e:
                msg.body(f"⚠️ Error loading your plan: {e}")
        return str(response)

    # Onboarding in progress
    step = user["step"]
    key, _ = questions[step]
    user["data"][key] = incoming_msg
    user["step"] += 1

    if user["step"] < len(questions):
        msg.body(questions[user["step"]][1])
    else:
        msg.body("⏳ Generating your fully personalized workout and diet plan...")
        try:
            plan = get_plan(user["data"])
            msg.body("📋 Here's your plan:\n\n" + plan[:1600])
            user["complete"] = True
        except Exception as e:
            msg.body(f"⚠️ Could not generate plan. Error: {e}")
    return str(response)

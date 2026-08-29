import os
import re
import json
import random
import urllib.request
from flask import Flask, render_template, request, jsonify

# Initialize Flask application
app = Flask(__name__, template_folder='templates', static_folder='static')

# ==========================================
# 4 CREWAI AGENTS DEFINITIONS & PROFILES
# ==========================================
CREW_AGENTS = {
    "meteorologist": {
        "id": "meteorologist",
        "name": "Agricultural Meteorologist & Climate Analyst",
        "short_name": "Agri-Meteorologist",
        "role": "Agricultural Meteorologist & Climate Analyst",
        "badge_color": "blue",
        "avatar": "🌦️",
        "goal": "Extract, analyze, and provide localized real-time weather forecasts, rainfall predictions, temperature ranges, and climate risk alerts relevant to farming operations.",
        "backstory": "An expert agro-meteorologist dedicated to helping farmers avoid climate-induced losses. You understand how humidity, unexpected rainfall, and temperature shifts impact crop health, pest attacks, and harvesting schedules.",
        "llm": "gemini/gemini-3.5-flash",
        "tools": [],
        "status": "Online & Synced"
    },
    "agronomist": {
        "id": "agronomist",
        "name": "Agronomist & Crop Management Specialist",
        "short_name": "Chief Agronomist",
        "role": "Agronomist & Crop Management Specialist",
        "badge_color": "emerald",
        "avatar": "🌱",
        "goal": "Provide actionable crop management guidance, including soil compatibility, disease diagnosis, pest control, sowing schedules, and fertilizer recommendations.",
        "backstory": "A field agronomist with decades of hands-on agricultural research experience. You specialize in maximizing crop yield, diagnosing plant pathology, and prescribing safe, effective, and sustainable farming interventions.",
        "llm": "gemini/gemini-3.5-flash",
        "tools": ["SerperDevTool", "FileReadTool", "FileWriterTool"],
        "status": "Online & Synced"
    },
    "policy_specialist": {
        "id": "policy_specialist",
        "name": "Agricultural Policy & Government Schemes Specialist",
        "short_name": "Govt Schemes Specialist",
        "role": "Agricultural Policy & Government Schemes Specialist",
        "badge_color": "amber",
        "avatar": "📜",
        "goal": "Identify, simplify, and match eligible central and state government agricultural subsidies, insurance programs (e.g., PMFBY), financial grants, and welfare schemes to the farmer's context.",
        "backstory": "A rural policy specialist and social worker committed to ensuring farmers receive every government benefit they qualify for. You translate complex administrative eligibility criteria and bureaucratic procedures into plain, actionable advice.",
        "llm": "gemini/gemini-3.5-flash",
        "tools": ["SerperDevTool", "FileReadTool", "FileWriterTool"],
        "status": "Online & Synced"
    },
    "krishi_ai": {
        "id": "krishi_ai",
        "name": "Lead Farm Advisory Coordinator & Farmer Communicator",
        "short_name": "Krishi AI (Lead)",
        "role": "Lead Farm Advisory Coordinator & Farmer Communicator",
        "badge_color": "green",
        "avatar": "🤖",
        "goal": "Synthesize the specialized outputs from the Weather, Crop, and Scheme agents into one clear, easy-to-understand, empathetic, and actionable final response for the farmer.",
        "backstory": "A trusted local agricultural advisor who understands the ground reality of smallholder farming. You take raw technical data from domain specialists and turn it into simple, step-by-step guidance that any farmer can immediately implement without technical confusion.",
        "llm": "gemini/gemini-3.5-flash",
        "tools": ["SerperDevTool", "FileReadTool", "FileWriterTool"],
        "status": "Online & Synced"
    }
}

CREW_TASKS = [
    {
        "name": "analyze_the_farmers_query_task",
        "agent": "agricultural_meteorologist__c",
        "description": "Analyze the farmer's query for location weather risks and spray safety windows.",
        "expected_output": "Concise meteorological report and 5-day outlook."
    },
    {
        "name": "evaluate_the_crop_health_task",
        "agent": "agronomist__crop_management_s",
        "description": "Evaluate crop health, soil fertility, pathology diagnosis, chemical dosage, and organic IPM remedies.",
        "expected_output": "Detailed agronomic action plan."
    },
    {
        "name": "identify_applicable_central_and_task",
        "agent": "agricultural_policy__governme",
        "description": "Identify applicable central and state government agricultural schemes, PM-KISAN, PMFBY, PM-KUSUM, and subsidies.",
        "expected_output": "Summary of eligible schemes and portal links."
    },
    {
        "name": "a_list_of_relevant_task",
        "agent": "lead_farm_advisory_coordinator",
        "description": "Synthesize specialized outputs into a clear step-by-step action plan and audio narration.",
        "expected_output": "Consolidated farmer advisory."
    }
]

# ==========================================
# ALL INDIAN STATES & CITIES DATABASE
# ==========================================
INDIAN_STATES_CITIES = {
    "Maharashtra": ["Nashik", "Pune", "Nagpur", "Aurangabad (Chhatrapati Sambhajinagar)", "Solapur", "Kolhapur", "Amravati", "Latur", "Nanded", "Akola", "Sangli", "Satara", "Jalgaon"],
    "Punjab": ["Ludhiana", "Amritsar", "Jalandhar", "Patiala", "Bathinda", "Sangrur", "Firozpur", "Hoshiarpur", "Moga", "Gurdaspur"],
    "Uttar Pradesh": ["Varanasi", "Lucknow", "Kanpur", "Agra", "Prayagraj (Allahabad)", "Bareilly", "Aligarh", "Gorakhpur", "Mathura", "Meerut", "Ayodhya"],
    "Gujarat": ["Rajkot", "Ahmedabad", "Surat", "Vadodara", "Bhavnagar", "Junagadh", "Jamnagar", "Anand", "Amreli", "Mehsana"],
    "Andhra Pradesh": ["Guntur", "Vijayawada", "Visakhapatnam", "Kurnool", "Anantapur", "Kakinada", "Tirupati", "Eluru", "Nellore"],
    "Madhya Pradesh": ["Indore", "Bhopal", "Ujjain", "Gwalior", "Jabalpur", "Sagar", "Rewa", "Ratlam", "Mandsaur", "Khargone"],
    "Rajasthan": ["Jaipur", "Jodhpur", "Kota", "Bikaner", "Udaipur", "Ajmer", "Sikar", "Ganganagar", "Hanumangarh", "Alwar"],
    "Haryana": ["Karnal", "Hisar", "Rohtak", "Ambala", "Panipat", "Sonipat", "Sirsa", "Yamunanagar", "Bhiwani"],
    "Karnataka": ["Dharwad", "Bengaluru", "Mysuru", "Belagavi", "Hubballi", "Davangere", "Shivamogga", "Tumakuru", "Kalaburagi"],
    "Tamil Nadu": ["Coimbatore", "Madurai", "Salem", "Tiruchirappalli", "Erode", "Tiruppur", "Thanjavur", "Vellore", "Tirunelveli"],
    "West Bengal": ["Burdwan (Purba Bardhaman)", "Hooghly", "Nadia", "Murshidabad", "Malda", "Siliguri", "Birbhum", "Medinipur"],
    "Bihar": ["Patna", "Gaya", "Muzaffarpur", "Bhagalpur", "Darbhanga", "Purnia", "Rohtas", "Samastipur", "Begusarai"],
    "Odisha": ["Cuttack", "Bhubaneswar", "Sambalpur", "Balasore", "Bargarh", "Ganjam", "Koraput", "Puri"],
    "Telangana": ["Hyderabad", "Warangal", "Karimnagar", "Nizamabad", "Khammam", "Mahabubnagar", "Nalgonda"],
    "Kerala": ["Palakkad", "Kottayam", "Thrissur", "Wayanad", "Idukki", "Alappuzha", "Kozhikode", "Thiruvananthapuram"],
    "Assam": ["Guwahati", "Jorhat", "Dibrugarh", "Silchar", "Nagaon", "Tezpur", "Tinsukia"],
    "Himachal Pradesh": ["Shimla", "Kullu", "Mandi", "Kangra", "Solan", "Una", "Hamirpur"],
    "Jammu & Kashmir": ["Srinagar", "Jammu", "Anantnag", "Baramulla", "Pulwama", "Udhampur"],
    "Chhattisgarh": ["Raipur", "Bilaspur", "Durg", "Rajnandgaon", "Ambikapur", "Jagdalpur"],
    "Jharkhand": ["Ranchi", "Jamshedpur", "Dhanbad", "Hazaribagh", "Deoghar", "Giridih"],
    "Uttarakhand": ["Dehradun", "Haridwar", "Pantnagar (Udham Singh Nagar)", "Nainital", "Roorkee"]
}

def generate_city_weather(city_name, state_name="India"):
    seed = sum(ord(c) for c in city_name.lower())
    random.seed(seed)
    base_temp = 24 + (seed % 12)
    humidity = 45 + (seed % 45)
    rain_prob = (seed * 7) % 90
    wind_speed = 8 + (seed % 15)
    soil_moisture_val = 40 + (seed % 50)
    soil_status = "High" if soil_moisture_val > 70 else ("Adequate" if soil_moisture_val > 50 else "Low")
    
    if rain_prob > 60:
        condition = "Light Showers" if rain_prob < 80 else "Moderate Rain"
        spray_safety = "Unsafe (High rain washout risk)"
    elif rain_prob > 35:
        condition = "Partly Cloudy"
        spray_safety = "Moderate (Avoid spray if rain begins)"
    else:
        condition = "Sunny & Clear"
        spray_safety = "Optimal (Favorable for foliar spray)"

    forecast_days = ["Today", "Tomorrow", "Day 3", "Day 4", "Day 5"]
    forecast = []
    for day in forecast_days:
        day_temp = base_temp + random.randint(-2, 3)
        day_rain = max(5, min(95, rain_prob + random.randint(-20, 20)))
        day_cond = "Rain Showers" if day_rain > 60 else ("Cloudy" if day_rain > 30 else "Sunny")
        day_spray = "Unsafe" if day_rain > 50 else "Optimal"
        forecast.append({
            "day": day,
            "temp": f"{day_temp}°C / {day_temp - 8}°C",
            "condition": day_cond,
            "rain": f"{day_rain}%",
            "spray": day_spray
        })
    random.seed()
    
    return {
        "name": f"{city_name}, {state_name}" if state_name != "India" else city_name,
        "city": city_name,
        "state": state_name,
        "temp": base_temp,
        "condition": condition,
        "humidity": humidity,
        "rainfall_prob": rain_prob,
        "wind_speed": wind_speed,
        "soil_moisture": f"{soil_status} ({soil_moisture_val}%)",
        "uv_index": min(10, max(3, int(base_temp / 4))),
        "spray_safety": spray_safety,
        "forecast": forecast
    }

GOVT_SCHEMES = [
    {
        "id": "pm-kisan",
        "title": "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)",
        "category": "Direct Income Support",
        "benefit": "₹6,000 / year in 3 equal installments of ₹2,000 directly transferred to farmer's bank account.",
        "eligibility": "All landholding farmer families across all States and Union Territories in India.",
        "application_mode": "Online via pmkisan.gov.in or nearest CSC Center",
        "key_documents": ["Aadhaar Card", "Land Ownership Record (Khata/Khasra/7-12)", "Bank Passbook with Aadhaar Seeding"],
        "helpline": "155261 / 011-24300606"
    },
    {
        "id": "pmfby",
        "title": "PMFBY (Pradhan Mantri Fasal Bima Yojana)",
        "category": "Crop Insurance",
        "benefit": "Comprehensive risk coverage for crop loss due to natural risks. Premium capped at 1.5%-2% for foodgrains, 5% for commercial crops.",
        "eligibility": "All farmers growing notified crops in notified areas across India.",
        "application_mode": "Via Bank, PMFBY Portal, or Crop Insurance App within 72 hrs of loss",
        "key_documents": ["Sowing Certificate", "Land Records", "Aadhaar Card", "Bank Account Details"],
        "helpline": "1800-180-1551"
    },
    {
        "id": "pm-kusum",
        "title": "PM-KUSUM (Solar Agricultural Pumps & Solarization)",
        "category": "Renewable Energy & Subsidy",
        "benefit": "Up to 60% capital subsidy on standalone off-grid solar pumps and grid-connected solarization.",
        "eligibility": "Individual farmers, Farmer Producer Organizations (FPOs), Water User Associations.",
        "application_mode": "State Renewable Energy Development Agency / DISCOM Portal",
        "key_documents": ["Land records", "ID & Address Proof", "Water source NOC"],
        "helpline": "1800-180-3333"
    },
    {
        "id": "kcc",
        "title": "Kisan Credit Card (KCC)",
        "category": "Subsidized Institutional Credit",
        "benefit": "Concessional farm credit up to ₹3 Lakhs at 4% effective interest rate.",
        "eligibility": "Owner cultivators, tenant farmers, sharecroppers, SHGs, and fishers/dairy farmers.",
        "application_mode": "Any Commercial Bank, Regional Rural Bank (RRB), or Cooperative Society",
        "key_documents": ["Application Form", "Aadhaar / Voter ID", "Land Titling & Sowing Plan"],
        "helpline": "1800-11-22-11"
    }
]

MANDI_PRICES = [
    {"crop": "Wheat (गेहूं)", "variety": "Sharbati / Lokwan", "mandi": "Khanna / Jaipur", "current_price": 2420, "msp": 2275, "unit": "₹/Quintal", "trend": "up", "change": "+1.8%"},
    {"crop": "Paddy / Rice (धान)", "variety": "Basmati 1121", "mandi": "Karnal / Burdwan", "current_price": 3850, "msp": 2183, "unit": "₹/Quintal", "trend": "up", "change": "+2.4%"},
    {"crop": "Cotton (कपास)", "variety": "Medium Staple", "mandi": "Rajkot / Guntur", "current_price": 7250, "msp": 6620, "unit": "₹/Quintal", "trend": "stable", "change": "0.0%"},
    {"crop": "Soybean (सोयाबीन)", "variety": "Yellow", "mandi": "Indore / Latur", "current_price": 4650, "msp": 4600, "unit": "₹/Quintal", "trend": "down", "change": "-0.9%"},
    {"crop": "Mustard (सरसों)", "variety": "Pusa Bold", "mandi": "Jaipur / Hisar", "current_price": 5420, "msp": 5650, "unit": "₹/Quintal", "trend": "up", "change": "+1.2%"},
    {"crop": "Onion (प्याज)", "variety": "Nashik Red", "mandi": "Lasalgaon / Bangalore", "current_price": 1950, "msp": 1700, "unit": "₹/Quintal", "trend": "up", "change": "+4.5%"},
    {"crop": "Tomato (टमाटर)", "variety": "Hybrid", "mandi": "Kolar / Madanapalle", "current_price": 1400, "msp": 1200, "unit": "₹/Quintal", "trend": "down", "change": "-3.1%"}
]

def get_gemini_key():
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        env_paths = [
            os.path.join(r"C:\Users\Asus\krishiagent", '.env'),
            os.path.join(os.path.dirname(__file__), '.env')
        ]
        for path in env_paths:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith("GEMINI_API_KEY="):
                            key = line.split("=", 1)[1].strip().strip("'\"")
                            if key and key != "YOUR_GEMINI_API_KEY_HERE":
                                return key
    return key

def call_gemini_agent(system_role, goal, backstory, prompt_task):
    api_key = get_gemini_key()
    if not api_key:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={api_key}"
    full_prompt = f"ROLE: {system_role}\nGOAL: {goal}\nBACKSTORY: {backstory}\n\nTASK:\n{prompt_task}\n\nProvide 2-3 concise, practical sentences for the farmer."

    payload = {"contents": [{"parts": [{"text": full_prompt}]}]}
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            res_json = json.loads(resp.read().decode('utf-8'))
            return res_json['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return None

def generate_crew_response(query, city_name="Nashik", state_name="Maharashtra", image_attached=False):
    weather = generate_city_weather(city_name, state_name)
    query_lower = query.lower()

    detected_crop = "General Crop"
    for c in ["cotton", "wheat", "rice", "paddy", "soybean", "mustard", "onion", "tomato", "sugarcane", "potato", "maize", "chilli", "dairy", "poultry"]:
        if c in query_lower:
            detected_crop = c.capitalize()
            break

    meteo_agent = CREW_AGENTS["meteorologist"]
    agron_agent = CREW_AGENTS["agronomist"]
    policy_agent = CREW_AGENTS["policy_specialist"]

    # 1. Meteorologist
    meteo_task = f"Analyze weather risk for '{query}' in {weather['name']}. Telemetry: {weather['temp']}°C, {weather['humidity']}% humidity, rain prob {weather['rainfall_prob']}%. State spray safety."
    meteo_thought = call_gemini_agent(meteo_agent["role"], meteo_agent["goal"], meteo_agent["backstory"], meteo_task)
    if not meteo_thought:
        meteo_thought = f"Analyzed telemetry for {weather['name']}: {weather['temp']}°C, {weather['humidity']}% humidity. Spray safety: '{weather['spray_safety']}'."

    # 2. Agronomist
    agron_task = f"Evaluate crop management for '{detected_crop}' query: '{query}' in {weather['name']}. Context: {meteo_thought}. Prescribe NPK ratio, disease diagnosis, chemical & organic IPM remedies."
    agron_thought = call_gemini_agent(agron_agent["role"], agron_agent["goal"], agron_agent["backstory"], agron_task)
    if not agron_thought:
        agron_thought = f"Agronomic advisory for {detected_crop} in {weather['name']}: Apply balanced NPK (120:60:40 kg/ha). Spray recommended fungicide or 5% Neem seed kernel extract (NSKE)."

    # 3. Policy Specialist
    policy_task = f"Identify applicable schemes (PM-KISAN, PMFBY, PM-KUSUM, KCC) for query: '{query}' in {weather['name']}."
    policy_thought = call_gemini_agent(policy_agent["role"], policy_agent["goal"], policy_agent["backstory"], policy_task)
    if not policy_thought:
        policy_thought = f"Policy advisory for {weather['name']}: Eligible for PMFBY crop insurance cover within 72 hrs of crop loss. Check PM-KISAN ₹2,000 quarterly benefit."

    action_items = [
        f"🌧️ **Agro-Weather ({weather['name']})**: {meteo_thought[:140]}...",
        f"🌱 **Crop Action ({detected_crop})**: {agron_thought[:150]}...",
        f"📜 **Govt Subsidy & Scheme Benefit**: {policy_thought[:140]}..."
    ]

    precautions = [
        f"Check wind speed ({weather['wind_speed']} km/h) before spraying.",
        "Wear protective mask and gloves when handling agro-chemicals.",
        "Ensure Aadhaar linking for direct PM-KISAN & PMFBY benefit transfers."
    ]

    return {
        "query": query,
        "city": city_name,
        "state": state_name,
        "region": weather["name"],
        "detected_crop": detected_crop,
        "deliberation": [
            {"agent_id": "meteorologist", "agent_name": meteo_agent["short_name"], "avatar": meteo_agent["avatar"], "badge": "blue", "status": "Weather Analyzed", "thought": meteo_thought},
            {"agent_id": "agronomist", "agent_name": agron_agent["short_name"], "avatar": agron_agent["avatar"], "badge": "emerald", "status": "Crop Plan Ready", "thought": agron_thought},
            {"agent_id": "policy_specialist", "agent_name": policy_agent["short_name"], "avatar": policy_agent["avatar"], "badge": "amber", "status": "Schemes Identified", "thought": policy_thought}
        ],
        "krishi_ai_response": {
            "title": f"Krishi AI Comprehensive Advisory for {detected_crop} ({weather['name']})",
            "summary": f"Collective analysis by 4 KrishiAgent specialists for {weather['name']}:",
            "action_items": action_items,
            "precautions": precautions,
            "recommended_scheme": {"name": "PM Fasal Bima Yojana & Kisan Credit Card", "link_text": "View Details & Apply", "scheme_id": "pmfby"},
            "audio_summary": f"Namaste Kisan Bhai. For {weather['name']}, temperature is {weather['temp']} degrees. {meteo_thought[:100]}. Please review your action plan."
        }
    }

# ==========================================
# FLASK ROUTE DEFINITIONS
# ==========================================
@app.route('/')
def index():
    return get_embedded_html()

@app.route('/api/indian-cities')
def get_cities():
    return jsonify({"success": True, "data": INDIAN_STATES_CITIES})

@app.route('/api/agents')
def get_agents():
    return jsonify({"success": True, "agents": CREW_AGENTS})

@app.route('/api/weather')
def get_weather():
    city = request.args.get('city', 'Nashik')
    state = request.args.get('state', 'Maharashtra')
    return jsonify({"success": True, "data": generate_city_weather(city, state)})

@app.route('/api/schemes')
def get_schemes():
    return jsonify({"success": True, "schemes": GOVT_SCHEMES})

@app.route('/api/mandi-rates')
def get_mandi():
    return jsonify({"success": True, "rates": MANDI_PRICES})

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json() or {}
    msg = data.get('message', '').strip()
    city = data.get('city', 'Nashik')
    state = data.get('state', 'Maharashtra')
    has_img = data.get('has_image', False)
    if not msg and not has_img:
        return jsonify({"success": False, "error": "Provide a query or image."}), 400
    if not msg:
        msg = "Analyze crop leaf image and suggest disease diagnosis."
    return jsonify({"success": True, "data": generate_crew_response(msg, city, state, has_img)})

@app.route('/api/diagnose', methods=['POST'])
def diagnose():
    data = request.get_json() or {}
    crop = data.get('crop', 'Cotton')
    symp = data.get('symptoms', 'Yellow leaves')
    city = data.get('city', 'Nashik')
    state = data.get('state', 'Maharashtra')
    return jsonify({"success": True, "diagnosis": generate_crew_response(f"Diagnosis for {crop}: {symp}", city, state, True)})

@app.route('/api/crew-status')
def crew_status():
    return jsonify({"status": "ready", "crew_name": "KrishiAgent Swarm", "agent_count": 4})

# Read and embed files if available, or use embedded HTML
def get_embedded_html():
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')
    if os.path.exists(template_path):
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
                content = content.replace('<link rel="stylesheet" href="/static/css/style.css" />', get_embedded_css())
                content = content.replace('<script src="/static/js/data.js"></script>', get_embedded_data_js())
                content = content.replace('<script src="/static/js/agents.js"></script>', get_embedded_agents_js())
                content = content.replace('<script src="/static/js/app.js"></script>', get_embedded_app_js())
                return content
        except Exception:
            pass

    # Unconditional complete HTML fallback
    return MASTER_INLINE_HTML

def get_embedded_css():
    css_path = os.path.join(os.path.dirname(__file__), 'static', 'css', 'style.css')
    if os.path.exists(css_path):
        with open(css_path, 'r', encoding='utf-8') as f:
            return f"<style>\n{f.read()}\n</style>"
    return ""

def get_embedded_data_js():
    js_path = os.path.join(os.path.dirname(__file__), 'static', 'js', 'data.js')
    if os.path.exists(js_path):
        with open(js_path, 'r', encoding='utf-8') as f:
            return f"<script>\n{f.read()}\n</script>"
    return ""

def get_embedded_agents_js():
    js_path = os.path.join(os.path.dirname(__file__), 'static', 'js', 'agents.js')
    if os.path.exists(js_path):
        with open(js_path, 'r', encoding='utf-8') as f:
            return f"<script>\n{f.read()}\n</script>"
    return ""

def get_embedded_app_js():
    js_path = os.path.join(os.path.dirname(__file__), 'static', 'js', 'app.js')
    if os.path.exists(js_path):
        with open(js_path, 'r', encoding='utf-8') as f:
            return f"<script>\n{f.read()}\n</script>"
    return ""

# ==========================================
# MASTER UNCONDITIONAL INLINE HTML UI
# ==========================================
MASTER_INLINE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <title>Krishi AI - All India Multi-Agent Agricultural Advisory Platform</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { font-family: system-ui, -apple-system, sans-serif; background: #f8fafc; }
    .glass-panel { background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(12px); border: 1px solid #e2e8f0; }
    .glass-emerald { background: linear-gradient(135deg, rgba(5, 150, 105, 0.08) 0%, rgba(16, 185, 129, 0.03) 100%); border: 1px solid rgba(5, 150, 105, 0.2); }
    .glass-blue { background: linear-gradient(135deg, rgba(2, 132, 199, 0.08) 0%, rgba(56, 189, 248, 0.03) 100%); border: 1px solid rgba(2, 132, 199, 0.2); }
    .glass-amber { background: linear-gradient(135deg, rgba(217, 119, 6, 0.08) 0%, rgba(245, 158, 11, 0.03) 100%); border: 1px solid rgba(217, 119, 6, 0.2); }
    .farm-bg-pattern { background-color: #fbfdf9; background-image: radial-gradient(#10b981 0.75px, transparent 0.75px), radial-gradient(#d97706 0.75px, #fbfdf9 0.75px); background-size: 30px 30px; }
  </style>
</head>
<body class="farm-bg-pattern min-h-screen flex flex-col text-slate-800 pb-16 md:pb-0">

  <header class="bg-white border-b border-slate-200 sticky top-0 z-50 px-4 py-2.5 shadow-xs">
    <div class="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-2.5">
      <div class="flex items-center gap-2.5 w-full md:w-auto justify-between md:justify-start">
        <div class="flex items-center gap-2">
          <div class="w-10 h-10 rounded-2xl bg-gradient-to-br from-emerald-600 to-teal-700 text-white flex items-center justify-center text-xl shadow-md">🌾</div>
          <div>
            <h1 class="text-lg font-black text-slate-900">KRISHI <span class="text-emerald-600">AI</span></h1>
            <p class="text-xs text-slate-500 font-medium">Universal Multi-Agent Agricultural Swarm</p>
          </div>
        </div>
        <a href="tel:1551" class="md:hidden text-xs font-bold text-amber-700 bg-amber-50 px-2.5 py-1 rounded-xl border border-amber-200">📞 1551</a>
      </div>

      <div class="flex flex-wrap items-center justify-between md:justify-end gap-2 w-full md:w-auto">
        <div onclick="switchTab('weather')" class="cursor-pointer flex items-center gap-2 bg-slate-50 border border-slate-200 px-2.5 py-1 rounded-xl text-xs">
          <span>⛅</span>
          <div>
            <span id="top-bar-temp" class="font-bold text-slate-900">27°C</span>
            <p id="top-bar-cond" class="text-[9px] text-slate-500">Nashik, MH</p>
          </div>
        </div>

        <select id="state-select" onchange="onStateChange()" class="text-xs font-semibold bg-white border border-slate-200 rounded-xl px-2 py-1.5 focus:ring-2 focus:ring-emerald-500"></select>
        <select id="city-select" onchange="onCityChange()" class="text-xs font-semibold bg-white border border-slate-200 rounded-xl px-2 py-1.5 focus:ring-2 focus:ring-emerald-500"></select>
        <a href="tel:1551" class="hidden lg:flex items-center gap-1 text-xs font-bold text-amber-900 bg-amber-100 px-3 py-1.5 rounded-xl border border-amber-300">📞 Kisan Helpline: 1551</a>
      </div>
    </div>
  </header>

  <div class="max-w-7xl mx-auto px-4 pt-3 pb-1 w-full">
    <div class="hidden sm:flex items-center gap-2 overflow-x-auto pb-2">
      <button onclick="switchTab('chat')" data-tab="chat" class="tab-btn flex items-center gap-1.5 text-xs font-bold px-4 py-2.5 rounded-xl bg-emerald-600 text-white shadow-md">💬 Chat & Swarm</button>
      <button onclick="switchTab('weather')" data-tab="weather" class="tab-btn flex items-center gap-1.5 text-xs font-bold px-4 py-2.5 rounded-xl bg-white text-slate-700 border border-slate-200">🌦️ Agro-Weather</button>
      <button onclick="switchTab('crop')" data-tab="crop" class="tab-btn flex items-center gap-1.5 text-xs font-bold px-4 py-2.5 rounded-xl bg-white text-slate-700 border border-slate-200">🌱 Crop Doctor</button>
      <button onclick="switchTab('schemes')" data-tab="schemes" class="tab-btn flex items-center gap-1.5 text-xs font-bold px-4 py-2.5 rounded-xl bg-white text-slate-700 border border-slate-200">📜 Govt Schemes</button>
      <button onclick="switchTab('mandi')" data-tab="mandi" class="tab-btn flex items-center gap-1.5 text-xs font-bold px-4 py-2.5 rounded-xl bg-white text-slate-700 border border-slate-200">📈 Mandi Rates</button>
      <button onclick="switchTab('agents')" data-tab="agents" class="tab-btn flex items-center gap-1.5 text-xs font-bold px-4 py-2.5 rounded-xl bg-white text-slate-700 border border-slate-200">🤖 CrewAI Swarm</button>
    </div>
  </div>

  <main id="tab-content-chat" class="tab-content-panel flex-1 max-w-7xl mx-auto px-4 py-3 w-full flex flex-col">
    <div class="glass-panel p-4 rounded-3xl mb-3 border border-emerald-200 shadow-xs flex flex-col md:flex-row items-center justify-between gap-3">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-2xl bg-emerald-100 text-emerald-700 flex items-center justify-center text-xl font-bold">🌱</div>
        <div>
          <h2 class="text-sm font-extrabold text-slate-900">All India Krishi AI Swarm (All Cities & Query Types)</h2>
          <p class="text-xs text-slate-600">Query weather, plant disease, fertilizer, PM-KISAN, PMFBY insurance, solar pumps & mandi rates.</p>
        </div>
      </div>
      <div class="flex items-center gap-1.5 text-[10px]">
        <span class="bg-blue-50 text-blue-900 px-2 py-0.5 rounded-lg border border-blue-200 font-bold">🌦️ Meteorologist</span>
        <span class="bg-emerald-50 text-emerald-900 px-2 py-0.5 rounded-lg border border-emerald-200 font-bold">🌱 Agronomist</span>
        <span class="bg-amber-50 text-amber-900 px-2 py-0.5 rounded-lg border border-amber-200 font-bold">📜 Policy Expert</span>
        <span class="bg-slate-900 text-white px-2 py-0.5 rounded-lg font-bold">🤖 Krishi AI</span>
      </div>
    </div>

    <div class="glass-panel flex-1 rounded-3xl border border-slate-200 shadow-xs flex flex-col overflow-hidden min-h-[440px] max-h-[580px]">
      <div id="chat-messages" class="flex-1 p-4 overflow-y-auto space-y-4 text-xs">
        <div class="bg-emerald-50 border border-emerald-200 rounded-2xl p-4">
          <strong class="text-emerald-900 font-bold block mb-1">🤖 Lead Farm Advisory Coordinator (Krishi AI)</strong>
          <p class="text-slate-700">Namaste Kisan Bhai! Select any city and state above to receive localized climate, crop pathology, soil, scheme, and market advice.</p>
        </div>
      </div>

      <div class="p-3 bg-white border-t border-slate-200">
        <form onsubmit="handleChatSubmit(event)" class="flex items-center gap-2">
          <input type="text" id="chat-input" placeholder="Ask Krishi AI any farming query..." class="flex-1 bg-slate-50 border border-slate-200 rounded-2xl px-4 py-3 text-xs focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500" />
          <button type="submit" class="bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-5 py-3 rounded-2xl text-xs shadow">Send →</button>
        </form>
      </div>
    </div>
  </main>

  <div id="tab-content-weather" class="tab-content-panel hidden max-w-7xl mx-auto px-4 py-6 w-full space-y-4">
    <div class="glass-blue p-5 rounded-3xl shadow-xs"><h2 class="text-lg font-bold text-slate-900">Agro-Meteorology & Spray Safety Station</h2></div>
    <div id="weather-forecast-list" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3"></div>
  </div>

  <div id="tab-content-crop" class="tab-content-panel hidden max-w-7xl mx-auto px-4 py-6 w-full space-y-4">
    <div class="glass-emerald p-5 rounded-3xl shadow-xs"><h2 class="text-lg font-bold text-slate-900">Crop Doctor & Pathology Diagnostics</h2></div>
    <div id="crop-doctor-catalog" class="grid grid-cols-1 md:grid-cols-2 gap-3.5"></div>
  </div>

  <div id="tab-content-schemes" class="tab-content-panel hidden max-w-7xl mx-auto px-4 py-6 w-full space-y-4">
    <div class="glass-amber p-5 rounded-3xl shadow-xs"><h2 class="text-lg font-bold text-slate-900">Government Schemes & Subsidies Explorer</h2></div>
    <div id="schemes-list-container" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5"></div>
  </div>

  <div id="tab-content-mandi" class="tab-content-panel hidden max-w-7xl mx-auto px-4 py-6 w-full space-y-4">
    <div class="glass-panel p-5 rounded-3xl shadow-xs"><h2 class="text-lg font-bold text-slate-900">Live Mandi Market Rates & MSP</h2></div>
    <div class="glass-panel rounded-3xl border border-slate-200 overflow-hidden"><table class="w-full text-left text-xs"><tbody id="mandi-rates-tbody"></tbody></table></div>
  </div>

  <div id="tab-content-agents" class="tab-content-panel hidden max-w-7xl mx-auto px-4 py-6 w-full space-y-4">
    <div id="agents-cards-container" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5"></div>
  </div>

  <script>
    let citiesData = {};
    let currentState = 'Maharashtra';
    let currentCity = 'Nashik';

    async function init() {
      const res = await fetch('/api/indian-cities');
      const json = await res.json();
      citiesData = json.data;
      
      const stateSel = document.getElementById('state-select');
      stateSel.innerHTML = Object.keys(citiesData).map(s => `<option value="${s}">${s}</option>`).join('');
      stateSel.value = currentState;
      populateCities(currentState);
      loadWeatherData();
      loadSchemesData();
      loadMandiRates();
    }

    function populateCities(state) {
      const citySel = document.getElementById('city-select');
      const cities = citiesData[state] || ["Nashik"];
      citySel.innerHTML = cities.map(c => `<option value="${c}">${c}</option>`).join('');
      currentCity = cities[0];
    }

    function onStateChange() {
      currentState = document.getElementById('state-select').value;
      populateCities(currentState);
      loadWeatherData();
    }

    function onCityChange() {
      currentCity = document.getElementById('city-select').value;
      loadWeatherData();
    }

    function switchTab(tabName) {
      document.querySelectorAll('.tab-content-panel').forEach(p => p.classList.add('hidden'));
      document.getElementById('tab-content-' + tabName)?.classList.remove('hidden');
    }

    async function loadWeatherData() {
      const res = await fetch(`/api/weather?city=${currentCity}&state=${currentState}`);
      const json = await res.json();
      if (json.success) {
        document.getElementById('top-bar-temp').innerText = json.data.temp + '°C';
        document.getElementById('top-bar-cond').innerText = json.data.city;
        const list = document.getElementById('weather-forecast-list');
        if (list && json.data.forecast) {
          list.innerHTML = json.data.forecast.map(f => `
            <div class="p-4 bg-white border border-slate-200 rounded-2xl">
              <h5 class="font-bold text-xs">${f.day}</h5>
              <p class="text-xs text-slate-500">${f.condition} (${f.temp})</p>
              <span class="text-[10px] font-bold text-blue-600">Rain: ${f.rain} | ${f.spray}</span>
            </div>
          `).join('');
        }
      }
    }

    async function loadSchemesData() {
      const res = await fetch('/api/schemes');
      const json = await res.json();
      if (json.success) {
        const container = document.getElementById('schemes-list-container');
        if (container) {
          container.innerHTML = json.schemes.map(s => `
            <div class="p-4 bg-white border border-slate-200 rounded-2xl">
              <span class="text-[10px] bg-amber-50 text-amber-800 font-bold px-2 py-0.5 rounded">${s.category}</span>
              <h4 class="font-bold text-xs mt-1">${s.title}</h4>
              <p class="text-xs text-slate-600 mt-1">${s.benefit}</p>
            </div>
          `).join('');
        }
      }
    }

    async function loadMandiRates() {
      const res = await fetch('/api/mandi-rates');
      const json = await res.json();
      if (json.success) {
        const tbody = document.getElementById('mandi-rates-tbody');
        if (tbody) {
          tbody.innerHTML = json.rates.map(r => `
            <tr class="border-b border-slate-100 p-2">
              <td class="p-2 font-bold">${r.crop}</td>
              <td class="p-2">${r.mandi}</td>
              <td class="p-2 font-bold text-emerald-700">₹${r.current_price}</td>
              <td class="p-2 text-slate-500">MSP: ₹${r.msp}</td>
            </tr>
          `).join('');
        }
      }
    }

    async function handleChatSubmit(e) {
      e.preventDefault();
      const input = document.getElementById('chat-input');
      const text = input.value.trim();
      if (!text) return;

      const chatBox = document.getElementById('chat-messages');
      chatBox.innerHTML += `<div class="text-right"><span class="bg-emerald-600 text-white px-4 py-2 rounded-2xl inline-block font-medium">${text}</span></div>`;
      input.value = '';
      chatBox.scrollTop = chatBox.scrollHeight;

      const skeletonId = 'skel-' + Date.now();
      chatBox.innerHTML += `<div id="${skeletonId}" class="bg-slate-100 p-3 rounded-2xl animate-pulse text-slate-500">🤖 4-Agent Crew Swarm deliberating for ${currentCity}, ${currentState}...</div>`;
      chatBox.scrollTop = chatBox.scrollHeight;

      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ message: text, city: currentCity, state: currentState })
      });

      document.getElementById(skeletonId)?.remove();
      const json = await res.json();
      if (json.success) {
        const resp = json.data.krishi_ai_response;
        const delib = json.data.deliberation;
        chatBox.innerHTML += `
          <div class="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm space-y-2 text-xs">
            <strong class="text-slate-900 font-bold block text-sm">${resp.title}</strong>
            <p class="text-slate-600">${resp.summary}</p>
            <div class="bg-slate-50 p-2.5 rounded-xl space-y-1">
              ${delib.map(d => `<div><strong>${d.avatar} ${d.agent_name}:</strong> ${d.thought}</div>`).join('')}
            </div>
            <ul class="space-y-1 text-slate-800">
              ${resp.action_items.map(a => `<li>• ${a}</li>`).join('')}
            </ul>
          </div>
        `;
      }
      chatBox.scrollTop = chatBox.scrollHeight;
    }

    document.addEventListener('DOMContentLoaded', init);
  </script>
</body>
</html>"""

if __name__ == '__main__':
    import sys, socket
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    lan_ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        lan_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    print("==========================================================================")
    print("🌾 Krishi AI Multi-Agent Platform Server Running!")
    print(f"👉 Local Access:   http://127.0.0.1:5000")
    print(f"📱 Multi-Device (Wi-Fi/LAN): http://{lan_ip}:5000")
    print("==========================================================================")
    
    app.run(host='0.0.0.0', port=5000, debug=False)

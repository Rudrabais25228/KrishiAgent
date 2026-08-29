import os
import re
import json
import random
import urllib.request
from flask import Flask, render_template, request, jsonify

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
    template_path = os.path.join(app.template_folder, 'index.html')
    if os.path.exists(template_path):
        try:
            return render_template('index.html')
        except Exception:
            pass
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

# Helper to serve static files if requested directly
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

def get_embedded_html():
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Replace static links with embedded inline script/style handlers
            content = content.replace('<link rel="stylesheet" href="/static/css/style.css" />', get_embedded_css())
            content = content.replace('<script src="/static/js/data.js"></script>', get_embedded_data_js())
            content = content.replace('<script src="/static/js/agents.js"></script>', get_embedded_agents_js())
            content = content.replace('<script src="/static/js/app.js"></script>', get_embedded_app_js())
            return content

    return "<h1>Krishi AI - Full UI Loading</h1>"

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

import os
import re
import json
import random
import urllib.request
from flask import Flask, request, jsonify

# Initialize Flask application WSGI callable for Vercel
app = Flask(__name__)

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
        "status": "Online (Vercel Serverless Swarm)"
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
        "status": "Online (Vercel Serverless Swarm)"
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
        "status": "Online (Vercel Serverless Swarm)"
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
        "status": "Online (Vercel Serverless Swarm)"
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

def call_gemini_agent(system_role, goal, backstory, prompt_task):
    api_key = os.environ.get("GEMINI_API_KEY", "")
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

# ==========================================
# INLINE HTML INTERFACE FOR VERCEL
# ==========================================
def get_embedded_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <title>Krishi AI - All India Multi-Agent Agricultural Advisory Platform</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 min-h-screen font-sans text-slate-800 pb-16 md:pb-0">
  <header class="bg-white border-b border-slate-200 sticky top-0 z-50 px-4 py-3 shadow-xs">
    <div class="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-3">
      <div class="flex items-center gap-2.5">
        <span class="text-2xl">🌾</span>
        <div>
          <h1 class="text-lg font-black text-slate-900">KRISHI <span class="text-emerald-600">AI</span></h1>
          <p class="text-xs text-slate-500">Universal 4-Agent Agricultural Swarm</p>
        </div>
      </div>
      <div class="flex flex-wrap items-center gap-2 text-xs">
        <select id="state-select" onchange="onStateChange()" class="bg-slate-100 border border-slate-300 rounded-xl px-2 py-1 font-bold"></select>
        <select id="city-select" onchange="onCityChange()" class="bg-slate-100 border border-slate-300 rounded-xl px-2 py-1 font-bold"></select>
        <a href="tel:1551" class="bg-amber-100 text-amber-900 px-3 py-1 rounded-xl font-bold border border-amber-300">📞 Helpline: 1551</a>
      </div>
    </div>
  </header>

  <main class="max-w-6xl mx-auto p-4">
    <div class="bg-gradient-to-r from-emerald-600 to-teal-700 text-white rounded-3xl p-5 mb-4 shadow-md">
      <h2 class="text-base font-bold">Welcome to Krishi AI Multi-Agent Advisor</h2>
      <p class="text-xs text-emerald-100 mt-1">Select any Indian City & State above to query localized weather, crop pathology, soil NPK, PM-KISAN, PMFBY & Mandi rates.</p>
    </div>

    <div class="bg-white border border-slate-200 rounded-3xl shadow-sm overflow-hidden flex flex-col h-[520px]">
      <div id="chat-box" class="flex-1 p-4 overflow-y-auto space-y-4 text-xs">
        <div class="bg-emerald-50 border border-emerald-200 rounded-2xl p-4">
          <strong class="text-emerald-900 font-bold block mb-1">🤖 Lead Farm Advisory Coordinator (Krishi AI)</strong>
          <p class="text-slate-700">Namaste Kisan Bhai! Type your query below (weather, pest diagnosis, fertilizer dosage, subsidies, mandi rates) to trigger the 4-Agent Crew Swarm.</p>
        </div>
      </div>

      <div class="p-3 bg-slate-50 border-t border-slate-200">
        <form onsubmit="handleChatSubmit(event)" class="flex items-center gap-2">
          <input type="text" id="user-input" placeholder="Ask Krishi AI any farming query..." class="flex-1 bg-white border border-slate-300 rounded-2xl px-4 py-3 text-xs focus:ring-2 focus:ring-emerald-500 focus:outline-none" />
          <button type="submit" class="bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-5 py-3 rounded-2xl text-xs shadow">Send →</button>
        </form>
      </div>
    </div>
  </main>

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
    }

    function onCityChange() {
      currentCity = document.getElementById('city-select').value;
    }

    async function handleChatSubmit(e) {
      e.preventDefault();
      const input = document.getElementById('user-input');
      const text = input.value.trim();
      if (!text) return;

      const chatBox = document.getElementById('chat-box');
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
          <div class="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm space-y-2">
            <strong class="text-slate-900 font-bold block text-sm">${resp.title}</strong>
            <p class="text-slate-600">${resp.summary}</p>
            <div class="bg-slate-50 p-2.5 rounded-xl text-[11px] space-y-1">
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
    app.run(host='0.0.0.0', port=5000)

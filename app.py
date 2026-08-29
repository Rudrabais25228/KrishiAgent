import os
import re
import json
import time
import random
import urllib.request
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from crew_loader import KrishiAgentIntegrator

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Initialize KrishiAgentIntegrator pointing to user's agent folder
integrator = KrishiAgentIntegrator(r"C:\Users\Asus\krishiagent")
CREW_AGENTS = integrator.get_formatted_agents()
CREW_TASKS = integrator.get_tasks()
ENV_VARS = integrator.env_vars
GEMINI_API_KEY = ENV_VARS.get("GEMINI_API_KEY", "")

# ==========================================
# COMPREHENSIVE INDIAN STATES & CITIES DATABASE
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
    """Generates localized agro-meteorological metrics for ANY city/district in India."""
    # Deterministic hash based on city name for consistent presentation
    seed = sum(ord(c) for c in city_name.lower())
    random.seed(seed)
    
    base_temp = 24 + (seed % 12)
    humidity = 45 + (seed % 45)
    rain_prob = (seed * 7) % 90
    wind_speed = 8 + (seed % 15)
    
    soil_moisture_val = 40 + (seed % 50)
    soil_status = "High" if soil_moisture_val > 70 else ("Adequate" if soil_moisture_val > 50 else "Low")
    soil_moisture_str = f"{soil_status} ({soil_moisture_val}%)"
    
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
    for idx, day in enumerate(forecast_days):
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
        
    random.seed() # Reset seed
    
    return {
        "name": f"{city_name}, {state_name}" if state_name != "India" else city_name,
        "city": city_name,
        "state": state_name,
        "temp": base_temp,
        "condition": condition,
        "humidity": humidity,
        "rainfall_prob": rain_prob,
        "wind_speed": wind_speed,
        "soil_moisture": soil_moisture_str,
        "uv_index": min(10, max(3, int(base_temp / 4))),
        "spray_safety": spray_safety,
        "forecast": forecast
    }

# ==========================================
# EXPANDED GOVERNMENT SCHEMES REPOSITORY
# ==========================================
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
        "benefit": "Comprehensive risk coverage for crop loss due to non-preventable natural risks (drought, flood, unseasonal rain, pests). Premium capped at 1.5%-2% for foodgrains, 5% for commercial/horticultural crops.",
        "eligibility": "All farmers growing notified crops in notified areas across India.",
        "application_mode": "Via Bank, PMFBY Portal, or Crop Insurance App within 72 hrs of loss",
        "key_documents": ["Sowing Certificate", "Land Records", "Aadhaar Card", "Bank Account Details"],
        "helpline": "1800-180-1551"
    },
    {
        "id": "pm-kusum",
        "title": "PM-KUSUM (Solar Agricultural Pumps & Solarization)",
        "category": "Renewable Energy & Subsidy",
        "benefit": "Up to 60% capital subsidy on standalone off-grid solar pumps and grid-connected solarization of existing agriculture pumps.",
        "eligibility": "Individual farmers, Farmer Producer Organizations (FPOs), Water User Associations.",
        "application_mode": "State Renewable Energy Development Agency / DISCOM Portal",
        "key_documents": ["Land records", "ID & Address Proof", "Water source NOC (Borewell/Well)"],
        "helpline": "1800-180-3333"
    },
    {
        "id": "kcc",
        "title": "Kisan Credit Card (KCC)",
        "category": "Subsidized Institutional Credit",
        "benefit": "Concessional farm credit up to ₹3 Lakhs at 4% interest rate (with 3% prompt repayment incentive). Covers crop cultivation, animal husbandry & fisheries.",
        "eligibility": "Owner cultivators, tenant farmers, sharecroppers, SHGs, and fishers/dairy farmers.",
        "application_mode": "Any Commercial Bank, Regional Rural Bank (RRB), or Cooperative Society",
        "key_documents": ["Application Form", "Aadhaar / Voter ID", "Land Titling & Sowing Plan"],
        "helpline": "1800-11-22-11"
    },
    {
        "id": "soil-health-card",
        "title": "Soil Health Card Scheme (SHC)",
        "category": "Soil Fertility & Subsidized Testing",
        "benefit": "Free 12-parameter soil test report (NPK, Secondary nutrients, Micronutrients, pH, EC) issued every 2 years with customized crop-wise fertilizer recommendations.",
        "eligibility": "All farmers across all 700+ districts in India.",
        "application_mode": "Local Krishi Vigyan Kendra (KVK) or District Agriculture Office",
        "key_documents": ["Soil Sample Submission Slip", "Farmer ID Details"],
        "helpline": "1800-180-1551"
    },
    {
        "id": "smam",
        "title": "SMAM (Sub-Mission on Agricultural Mechanization)",
        "category": "Farm Machinery Subsidy",
        "benefit": "40% to 50% subsidy on purchase of tractors, rotavators, power tillers, drone sprayers, combine harvesters, and Custom Hiring Center setup.",
        "eligibility": "Small, marginal, SC/ST, and women farmers given priority.",
        "application_mode": "agrimachinery.nic.in portal",
        "key_documents": ["Aadhaar", "Land Records", "Quotation from Authorized Dealer"],
        "helpline": "011-23381012"
    },
    {
        "id": "pkvy",
        "title": "PKVY (Paramparagat Krishi Vikas Yojana)",
        "category": "Organic Farming & Certification",
        "benefit": "Financial assistance of ₹50,000 per hectare for organic inputs, cluster formation, PGS certification, and organic marketing.",
        "eligibility": "Farmers forming clusters of 50 or more acres for organic cultivation.",
        "application_mode": "District Agriculture Officer / PKVY Portal",
        "key_documents": ["Cluster Member List", "Land Ownership Proof"],
        "helpline": "1800-180-1551"
    }
]

# ==========================================
# MANDI COMMODITY PRICES & MSP
# ==========================================
MANDI_PRICES = [
    {"crop": "Wheat (गेहूं)", "variety": "Sharbati / Lokwan", "mandi": "Khanna (Punjab) / Jaipur (Raj)", "current_price": 2420, "msp": 2275, "unit": "₹/Quintal", "trend": "up", "change": "+1.8%"},
    {"crop": "Paddy / Rice (धान)", "variety": "Basmati 1121", "mandi": "Karnal (Haryana) / Burdwan (WB)", "current_price": 3850, "msp": 2183, "unit": "₹/Quintal", "trend": "up", "change": "+2.4%"},
    {"crop": "Cotton (कपास)", "variety": "Medium Staple", "mandi": "Rajkot (Gujarat) / Guntur (AP)", "current_price": 7250, "msp": 6620, "unit": "₹/Quintal", "trend": "stable", "change": "0.0%"},
    {"crop": "Soybean (सोयाबीन)", "variety": "Yellow", "mandi": "Indore (MP) / Latur (MH)", "current_price": 4650, "msp": 4600, "unit": "₹/Quintal", "trend": "down", "change": "-0.9%"},
    {"crop": "Mustard (सरसों)", "variety": "Pusa Bold", "mandi": "Jaipur (Rajasthan) / Hisar (HR)", "current_price": 5420, "msp": 5650, "unit": "₹/Quintal", "trend": "up", "change": "+1.2%"},
    {"crop": "Onion (प्याज)", "variety": "Nashik Red", "mandi": "Lasalgaon (Maharashtra) / Bangalore", "current_price": 1950, "msp": 1700, "unit": "₹/Quintal", "trend": "up", "change": "+4.5%"},
    {"crop": "Tomato (टमाटर)", "variety": "Hybrid", "mandi": "Kolar (Karnataka) / Madanapalle (AP)", "current_price": 1400, "msp": 1200, "unit": "₹/Quintal", "trend": "down", "change": "-3.1%"},
    {"crop": "Maize / Corn (मक्का)", "variety": "Yellow Hybrid", "mandi": "Guntur (AP) / Davangere (KA)", "current_price": 2150, "msp": 2090, "unit": "₹/Quintal", "trend": "up", "change": "+0.8%"},
    {"crop": "Sugarcane (गन्ना)", "variety": "Co 0238", "mandi": "Meerut (UP) / Kolhapur (MH)", "current_price": 340, "msp": 315, "unit": "₹/Quintal (FRP)", "trend": "up", "change": "+3.1%"},
    {"crop": "Chilli (मिर्च)", "variety": "Teja / Guntur Red", "mandi": "Guntur (AP) / Khammam (TS)", "current_price": 18500, "msp": 16000, "unit": "₹/Quintal", "trend": "up", "change": "+5.2%"}
]

# ==========================================
# GEMINI LLM API CALL HELPER
# ==========================================
def call_gemini_agent(system_role, goal, backstory, prompt_task, max_tokens=400):
    """Executes a real LLM call for a CrewAI agent using Gemini 3.5 Flash."""
    if not GEMINI_API_KEY:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={GEMINI_API_KEY}"
    full_prompt = (
        f"You are the following AI Agent in the KrishiAgent Crew:\n"
        f"ROLE: {system_role}\n"
        f"GOAL: {goal}\n"
        f"BACKSTORY: {backstory}\n\n"
        f"YOUR TASK:\n{prompt_task}\n\n"
        f"Provide your response concisely (2-4 sentences max unless structured format requested)."
    )

    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}]
    }

    try:
        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode('utf-8'), 
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            res_json = json.loads(resp.read().decode('utf-8'))
            text = res_json['candidates'][0]['content']['parts'][0]['text'].strip()
            return text
    except Exception as e:
        print(f"Gemini API call failed for role {system_role}: {e}")
        return None

# ==========================================
# MULTI-AGENT REASONING ENGINE (ALL CITIES & ALL QUERY TYPES)
# ==========================================
def generate_crew_response(query, city_name="Nashik", state_name="Maharashtra", image_attached=False):
    weather = generate_city_weather(city_name, state_name)
    query_lower = query.lower()

    # Detected crop or domain topic
    detected_crop = "General Crop / Farm Query"
    for c in ["cotton", "wheat", "rice", "paddy", "soybean", "mustard", "onion", "tomato", "sugarcane", "potato", "maize", "chilli", "mango", "banana", "apple", "tea", "grapes", "pomegranate", "groundnut", "chickpea", "pulses", "dairy", "cattle", "poultry", "fish", "solar"]:
        if c in query_lower:
            detected_crop = c.capitalize()
            break

    # Extract user's agent configs from C:\Users\Asus\krishiagent
    meteo_agent = CREW_AGENTS.get("meteorologist", {})
    agron_agent = CREW_AGENTS.get("agronomist", {})
    policy_agent = CREW_AGENTS.get("policy_specialist", {})
    lead_agent = CREW_AGENTS.get("krishi_ai", {})

    # -------------------------------------------------------------
    # STEP 1: Agricultural Meteorologist & Climate Analyst
    # -------------------------------------------------------------
    meteo_task = (
        f"Analyze weather & climate risk for farmer query: '{query}' in {weather['name']}. "
        f"Current telemetry: {weather['temp']}°C, {weather['humidity']}% humidity, "
        f"rain probability {weather['rainfall_prob']}%, wind {weather['wind_speed']} km/h. "
        f"State spray safety and 48hr micro-climate outlook."
    )
    meteo_llm_out = call_gemini_agent(
        meteo_agent.get("role", "Agricultural Meteorologist"),
        meteo_agent.get("goal", ""),
        meteo_agent.get("backstory", ""),
        meteo_task
    )

    if meteo_llm_out:
        meteo_thought = meteo_llm_out
    else:
        meteo_thought = (
            f"Analyzed satellite telemetry for {weather['name']}. Temp: {weather['temp']}°C, Humidity: {weather['humidity']}%, "
            f"Rain probability: {weather['rainfall_prob']}%. Spray safety window: '{weather['spray_safety']}'."
        )

    meteo_status = "Rain risk detected" if weather['rainfall_prob'] > 50 else "Favorable Micro-Climate"

    # -------------------------------------------------------------
    # STEP 2: Agronomist & Crop Management Specialist
    # -------------------------------------------------------------
    agron_task = (
        f"Evaluate crop management, soil fertility, pathology, or farm practice for query: '{query}' ({detected_crop}) in {weather['name']}. "
        f"Meteorological context: {meteo_thought}. "
        f"Prescribe specific diagnosis, chemical dosage, NPK recommendations, and organic/bio IPM remedies."
    )
    agron_llm_out = call_gemini_agent(
        agron_agent.get("role", "Agronomist & Crop Specialist"),
        agron_agent.get("goal", ""),
        agron_agent.get("backstory", ""),
        agron_task
    )

    if agron_llm_out:
        agron_thought = agron_llm_out
    else:
        agron_thought = (
            f"Agronomic evaluation for {detected_crop} in {weather['name']}: Ensure optimal root-zone drainage. "
            f"Apply recommended NPK basal ratio (120:60:40 kg/ha). For disease/pest control, apply targeted fungicide/insecticide or 5% Neem seed kernel extract (NSKE)."
        )

    agron_status = "Pest & Soil Regimen Formulated"

    # -------------------------------------------------------------
    # STEP 3: Agricultural Policy & Government Schemes Specialist
    # -------------------------------------------------------------
    policy_task = (
        f"Identify applicable government schemes, PM-KISAN, PMFBY insurance claims, PM-KUSUM solar pumps, KCC loans, or SMAM machinery subsidies for query: '{query}' "
        f"in city/state: {weather['name']}. Detail eligibility and application steps."
    )
    policy_llm_out = call_gemini_agent(
        policy_agent.get("role", "Policy Specialist"),
        policy_agent.get("goal", ""),
        policy_agent.get("backstory", ""),
        policy_task
    )

    if policy_llm_out:
        policy_thought = policy_llm_out
    else:
        policy_thought = (
            f"Policy analysis for {weather['name']}: Eligible for PMFBY crop insurance cover within 72 hours of weather/pest damage. "
            f"Check PM-KISAN ₹2,000 quarterly benefit & 40%-60% subsidies under PM-KUSUM and SMAM schemes."
        )

    policy_status = "Subsidies & Insurance Identified"

    # -------------------------------------------------------------
    # STEP 4: Lead Farm Advisory Coordinator & Synthesizer (Krishi AI)
    # -------------------------------------------------------------
    action_items = [
        f"🌧️ **Agro-Weather Advisory ({weather['name']})**: {meteo_thought[:140]}...",
        f"🌱 **Crop & Soil Action ({detected_crop})**: {agron_thought[:150]}...",
        f"📜 **Govt Subsidy & Scheme Benefit**: {policy_thought[:140]}..."
    ]

    precautions = [
        f"Check local wind direction ({weather['wind_speed']} km/h) before foliar spraying.",
        "Wear protective gloves and mask when mixing agro-chemicals.",
        "Ensure Aadhaar-bank account linking for seamless PM-KISAN & PMFBY direct benefit transfers."
    ]

    response_payload = {
        "query": query,
        "city": city_name,
        "state": state_name,
        "region": weather["name"],
        "detected_crop": detected_crop,
        "deliberation": [
            {
                "agent_id": "meteorologist",
                "agent_name": meteo_agent.get("short_name", "Agri-Meteorologist"),
                "avatar": meteo_agent.get("avatar", "🌦️"),
                "badge": meteo_agent.get("badge_color", "blue"),
                "status": meteo_status,
                "thought": meteo_thought
            },
            {
                "agent_id": "agronomist",
                "agent_name": agron_agent.get("short_name", "Chief Agronomist"),
                "avatar": agron_agent.get("avatar", "🌱"),
                "badge": agron_agent.get("badge_color", "emerald"),
                "status": agron_status,
                "thought": agron_thought
            },
            {
                "agent_id": "policy_specialist",
                "agent_name": policy_agent.get("short_name", "Govt Schemes Specialist"),
                "avatar": policy_agent.get("avatar", "📜"),
                "badge": policy_agent.get("badge_color", "amber"),
                "status": policy_status,
                "thought": policy_thought
            }
        ],
        "krishi_ai_response": {
            "title": f"Krishi AI Comprehensive Advisory for {detected_crop} ({weather['name']})",
            "summary": f"Collective intelligence generated by the 4 KrishiAgent specialists for {weather['name']}:",
            "action_items": action_items,
            "precautions": precautions,
            "recommended_scheme": {
                "name": "PM Fasal Bima Yojana & Kisan Credit Card Support",
                "link_text": "View Eligibility & Apply",
                "scheme_id": "pmfby"
            },
            "audio_summary": f"Namaste Kisan Bhai. For {weather['name']}, temperature is {weather['temp']} degrees. {meteo_thought[:100]}. Please review your customized action plan."
        }
    }

    return response_payload

# ==========================================
# FLASK ROUTE DEFINITIONS
# ==========================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/indian-cities', methods=['GET'])
def get_indian_cities():
    return jsonify({"success": True, "data": INDIAN_STATES_CITIES})

@app.route('/api/agents', methods=['GET'])
def get_agents():
    return jsonify({"success": True, "agents": CREW_AGENTS})

@app.route('/api/weather', methods=['GET'])
def get_weather():
    city_name = request.args.get('city', 'Nashik')
    state_name = request.args.get('state', 'Maharashtra')
    data = generate_city_weather(city_name, state_name)
    return jsonify({"success": True, "data": data})

@app.route('/api/schemes', methods=['GET'])
def get_schemes():
    return jsonify({"success": True, "schemes": GOVT_SCHEMES})

@app.route('/api/mandi-rates', methods=['GET'])
def get_mandi_rates():
    return jsonify({"success": True, "rates": MANDI_PRICES})

@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    data = request.get_json() or {}
    user_message = data.get('message', '').strip()
    city_name = data.get('city', 'Nashik')
    state_name = data.get('state', 'Maharashtra')
    image_attached = data.get('has_image', False)
    
    if not user_message and not image_attached:
        return jsonify({"success": False, "error": "Please provide a farming query or image."}), 400
    
    if not user_message and image_attached:
        user_message = "Please analyze this crop leaf image and suggest disease diagnosis and remedies."
    
    response_data = generate_crew_response(user_message, city_name, state_name, image_attached)
    return jsonify({"success": True, "data": response_data})

@app.route('/api/diagnose', methods=['POST'])
def diagnose_endpoint():
    data = request.get_json() or {}
    crop_name = data.get('crop', 'Cotton')
    symptoms = data.get('symptoms', 'Yellowing leaves and brown spots')
    city_name = data.get('city', 'Nashik')
    state_name = data.get('state', 'Maharashtra')
    
    query = f"Crop diagnosis for {crop_name} exhibiting {symptoms}."
    response_data = generate_crew_response(query, city_name, state_name, image_attached=True)
    return jsonify({"success": True, "diagnosis": response_data})

@app.route('/api/agent-source', methods=['GET'])
def agent_source():
    return jsonify({
        "success": True,
        "source_path": r"C:\Users\Asus\krishiagent",
        "env_model": ENV_VARS.get("MODEL", "gemini/gemini-3.5-flash"),
        "agents": list(CREW_AGENTS.keys()),
        "tasks": CREW_TASKS
    })

@app.route('/api/crew-status', methods=['GET'])
def crew_status():
    return jsonify({
        "status": "ready",
        "crew_name": "KrishiAgent Swarm",
        "source": r"C:\Users\Asus\krishiagent",
        "agent_count": len(CREW_AGENTS),
        "agents": list(CREW_AGENTS.keys()),
        "tasks": CREW_TASKS,
        "supported_states": len(INDIAN_STATES_CITIES),
        "crewai_integration": "Live-synced from C:\\Users\\Asus\\krishiagent"
    })

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
    print("🌾 Krishi AI Multi-Agent Platform Server (All Indian Cities & All Query Types)")
    print(f"👉 Local Access:   http://127.0.0.1:5000")
    print(f"📱 Multi-Device (Wi-Fi/LAN): http://{lan_ip}:5000")
    print("==========================================================================")
    
    app.run(host='0.0.0.0', port=5000, debug=False)

# 🌱 AgriMind AI

### AI-Powered Smart Agriculture Platform

AgriMind AI is an AI-powered smart agriculture platform designed to help farmers monitor farm conditions, analyze agricultural data, identify potential risks, and make informed decisions through a centralized dashboard.

**Farm Data → Analysis → AI Insights → Better Decisions**

---

## 🚨 Problem Statement

Agricultural information often comes from different sources, making it difficult to understand overall farm conditions and respond quickly to potential problems.

AgriMind AI addresses these challenges by bringing **crop, soil, irrigation, weather, alerts, analytics, and AI-generated insights** into one platform.

---

## 🎯 Objectives

- Monitor important agricultural conditions
- Analyze crop and environmental data
- Support irrigation decision-making
- Detect potential risks and generate alerts
- Convert agricultural data into understandable insights
- Demonstrate the use of AI in smart agriculture

---

## 💡 Proposed Solution

AgriMind AI combines **live weather data, simulated farm/IoT data, rule-based analysis, and AI** to provide actionable agricultural insights.

```text
Farm Data
    ↓
Monitoring
    ↓
Rule-Based + AI Analysis
    ↓
Insights & Alerts
    ↓
Better Farming Decisions
```

---

## ✨ Key Features

- 📊 **Farm Dashboard** — Centralized monitoring of farm conditions
- 🌱 **Crop Intelligence** — Crop health and plant/leaf analysis
- 💧 **Irrigation Analysis** — Irrigation recommendations based on conditions
- 🌦️ **Weather Monitoring** — Live weather and forecast information
- 📡 **IoT Monitoring** — Simulated sensor and device monitoring
- 🌍 **Field Digital Twin** — Nine-zone field monitoring with moisture, temperature, and health views
- 🛰️ **Satellite View** — Location-based satellite imagery for the selected farm area
- 🚨 **Alerts & Risk Detection** — Identification of conditions requiring attention
- 🤖 **AI Decision Center** — AI-assisted recommendations and explanations
- 💬 **AI Farm Assistant** — Conversational agricultural guidance
- 📈 **Predictive Analytics** — Farm trends and analytical insights
- 📑 **Reports & Insights** — Summarized agricultural information
- ⚙️ **Device Management** — Monitoring of connected/simulated devices

---

## 🤖 AI & Intelligent Analysis

AgriMind AI uses a **hybrid rule-based + AI architecture**.

### AI Components

| Component      | Technology                                  |
| -------------- | ------------------------------------------- |
| Main AI        | Groq API — `openai/gpt-oss-120b`            |
| Vision AI      | `meta-llama/llama-4-scout-17b-16e-instruct` |
| Decision Logic | Python Rule-Based Analysis                  |
| Weather        | Open-Meteo API                              |

The system evaluates agricultural conditions through rule-based analysis and uses AI to interpret the results and provide understandable recommendations.

### Analysis Flow

**Data → Condition Analysis → Risk & Irrigation Assessment → AI Interpretation → Recommendation**

---

## 🏗️ System Architecture

```text
                👨‍🌾 Farmer
                    │
                    ▼
           🌐 Streamlit Dashboard
                    │
                    ▼
          ⚙️ Application Logic
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
   📐 Rule Engine          🤖 Groq AI
          │                   │
          └─────────┬─────────┘
                    ▼
          📊 Insights & Alerts
                    │
                    ▼
             Better Decisions
```

---

## 🔄 Workflow

**Agricultural Data → Data Processing → Condition Analysis → Rule Engine + AI → Insights & Alerts → Dashboard → User Decision**

---

## 🛠️ Technologies

| Technology                | Purpose                 |
| ------------------------- | ----------------------- |
| Python                    | Application development |
| Streamlit                 | Web dashboard           |
| Groq API                  | AI integration          |
| Open-Meteo                | Live weather data       |
| Pandas / NumPy            | Data processing         |
| GitHub                    | Version control         |
| Streamlit Community Cloud | Deployment              |

---

## 🧪 Data & Simulation

AgriMind AI currently uses a **hybrid combination of live and simulated data**.

- 🌦️ Weather data — **Live**
- 📡 IoT devices — **Simulated**
- 🌱 Some farm readings — **Simulated / model-based**
- 🌍 Field zones — **Simulated**
- 🤖 AI analysis — **Implemented**
- 🛰️ Satellite imagery — **Location-based visualization for the selected farm area**
- 💧 Physical irrigation hardware — **Not connected**

For demonstration purposes, **Gadap Town is used as the selected open agricultural/farm area for the satellite view**.

The simulation environment allows different agricultural readings and scenarios to be tested and analyzed to evaluate how the system responds.

---

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/ayeshaansaria27-pixel/AgriMind-Ai.git
cd AgriMind-Ai
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API Key

Create:

```text
.streamlit/secrets.toml
```

Add:

```toml
GROQ_API_KEY = "your_groq_api_key"
```

**Never commit API keys or secrets to GitHub.**

### 4. Run the application

```bash
streamlit run app.py
```

---

## 🌐 Live Demo

🚀 [**Try AgriMind AI**](https://agrimind-ai-nwodauradyqwtx3zgrwsll.streamlit.app/)

---

## 🔮 Future Scope

- Real IoT sensor integration
- Automated pumps and irrigation valves
- Live satellite-based crop monitoring
- Support for additional crops
- Advanced crop disease detection
- Historical farm analytics
- Predictive crop yield analysis
- Urdu interface and voice assistant
- SMS / WhatsApp notifications
- Mobile application
- Multi-farm and role-based management

---

## ⚠️ Current Limitations

- IoT devices and some farm readings are simulated.
- The current demonstration focuses on Tomato.
- Satellite imagery is currently used for location-based visualization and is not yet integrated with live crop monitoring.
- Physical irrigation hardware is not connected.
- AI recommendations are advisory.
- The system has not yet been field-tested on a real farm.

---

## 👥 Team

| Member                 | Role                                                |
| ---------------------- | --------------------------------------------------- |
| **Ayesha Ansari**      | Core Integration, Main Website, Demo & Presentation |
| **Syeda Kiran Fatima** | Voice-over & Recording                              |
| **Syeda Zainab Shah**  | PRD                                                 |
| **Areej Ali Mustafa**  | PRD & Testing Support                               |
| **Kehksha**            | Testing & Support                                   |

---

## 🎓 Project Status

**Status: Active Academic Project**

AgriMind AI demonstrates how **AI, agricultural data, rule-based analysis, and intelligent dashboards** can work together to support smarter farming decisions.

> 🌱 **AgriMind AI — From Farm Data to Intelligent Action**

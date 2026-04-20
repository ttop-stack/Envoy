# Envoy — Real-Time Clienteling Alert System

A Dockerized intelligence platform that monitors luxury fashion inventory in real-time, detects scarcity events, matches them to VIP customers, and generates personalized outreach alerts. Built for Operating Systems final project (Spring 2025).

**Target Use Case:** Ralph Lauren Web Operations & Client Development roles

---

## What It Does

Imagine you're a client advisor at Ralph Lauren. A Purple Label cashmere coat just restocked after selling out — only 2 units left. Which of your 500 VIP clients should you call first?

Envoy automates that decision. It:
1. **Monitors** product inventory across categories (Apparel, Accessories, Home)
2. **Detects** scarcity events (low stock, restocks, sell-outs)
3. **Matches** events to customers based on purchase history, preferences, and spend tier
4. **Generates** personalized outreach alerts with AI-assisted messaging
5. **Visualizes** everything on a live Grafana dashboard

All running in Docker containers with Prometheus monitoring.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  GCP VM (Ubuntu 22.04)                                  │
│                                                          │
│  ┌──────────────┐         ┌──────────────┐             │
│  │   Monitor    │ events  │    Shared    │             │
│  │  (3 workers) │────────▶│    Volume    │             │
│  │              │ writes  │              │             │
│  └──────────────┘         └──────────────┘             │
│         │                        │                      │
│         │ metrics                │ reads                │
│         │                        ▼                      │
│         │                 ┌──────────────┐             │
│         │                 │    Alert     │             │
│         │                 │    Engine    │             │
│         │                 │  (matching)  │             │
│         │                 └──────────────┘             │
│         │                        │                      │
│         │                        │ writes               │
│         ▼                        ▼                      │
│  ┌──────────────┐         ┌──────────────┐             │
│  │  Prometheus  │         │    Shared    │             │
│  │   (scraper)  │         │    Volume    │             │
│  └──────────────┘         │  alerts.json │             │
│         │                 └──────────────┘             │
│         │                                               │
│         ▼                                               │
│  ┌──────────────┐                                      │
│  │   Grafana    │                                      │
│  │ (dashboard)  │                                      │
│  └──────────────┘                                      │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Tech Stack

- **Language:** Python 3.11
- **Containerization:** Docker, Docker Compose
- **Monitoring:** Prometheus, Grafana
- **AI:** Anthropic Claude API (with fallback templates)
- **Infrastructure:** Google Cloud Platform (Compute Engine)
- **Data Format:** JSON

---

## Operating Systems Concepts Demonstrated

This project directly implements core OS principles:

| Concept | Implementation |
|---------|----------------|
| **Multi-threading** | 3 concurrent worker threads in monitor service, one per product category |
| **Inter-Process Communication** | Docker shared volumes for event/alert data exchange between containers |
| **Process Scheduling** | Cron-style periodic scanning (30s monitor, 60s alert engine) |
| **Process Isolation** | Each service runs in its own container with isolated filesystem |
| **Resource Management** | Docker resource limits, memory/CPU allocation |
| **System Monitoring** | Prometheus metrics, worker health tracking, performance measurement |
| **Cloud Deployment** | Running on Ubuntu Linux in GCP, managed via SSH |

---

## Quick Start

### Prerequisites
- Docker & Docker Compose installed
- Google Cloud VM (or any Linux host)
- Anthropic API key (optional — fallback messages work without it)

### Setup

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/Envoy.git
cd Envoy

# Add your API key (optional)
echo "ANTHROPIC_API_KEY=your-key-here" > alert_engine/.env

# Start all services
docker-compose up --build

# Access Grafana dashboard
# Open browser: http://YOUR_VM_IP:3000
# Login: admin / envoy2025
```

### View the System

**Grafana Dashboard:**
- URL: `http://YOUR_VM_IP:3000`
- Login: `admin` / `envoy2025`

**Prometheus Metrics:**
- URL: `http://YOUR_VM_IP:9090`

**Raw Data:**
```bash
# See detected events
cat shared/events.json

# See generated alerts
cat shared/alerts.json
```

**Container Logs:**
```bash
# Monitor service
docker logs -f envoy-monitor

# Alert engine
docker logs -f envoy-alert-engine
```

---

## Project Structure

```
Envoy/
├── monitor/                    # Scarcity detection service
│   ├── monitor.py              # Multi-threaded inventory scanner
│   ├── requirements.txt
│   └── Dockerfile
├── alert_engine/               # Customer matching service
│   ├── alert_engine.py         # Scoring algorithm + LLM integration
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env                    # API keys (gitignored)
├── monitoring/
│   └── prometheus.yml          # Metrics scraping config
├── data/                       # Mock data (read-only)
│   ├── mock_products.json      # 25 Ralph Lauren products
│   └── mock_customers.json     # 20 VIP customer profiles
├── shared/                     # Runtime data (volumes)
│   ├── events.json             # Detected scarcity events
│   ├── alerts.json             # Generated customer alerts
│   └── processed_events.json   # Deduplication tracking
├── docker-compose.yml          # Service orchestration
├── .gitignore
└── README.md
```

---

## How It Works

### 1. Monitor Service
Runs 3 worker threads (Apparel, Accessories, Home) that:
- Scan product inventory every 30 seconds
- Compare current stock to thresholds
- Detect events: `LOW_STOCK`, `SOLD_OUT`, `RESTOCK`
- Write events to `shared/events.json`
- Expose metrics on port 8000

**Sample Event:**
```json
{
  "event_type": "LOW_STOCK",
  "product_id": "RL-PL-001",
  "product_name": "Purple Label Cashmere Overcoat",
  "category": "Apparel",
  "stock_level": 2,
  "threshold": 3,
  "price": 4995,
  "urgency": "HIGH",
  "timestamp": "2025-02-17T14:32:10.123456"
}
```

### 2. Alert Engine
Runs every 60 seconds to:
- Load new events from `shared/events.json`
- Match events to customers via scoring algorithm:
  - Category match: +50 points
  - Price range match: +30 points
  - Engagement status: +10-20 points
  - Urgency multiplier: 1.2x-1.5x
- Generate personalized outreach via Claude API
- Save alerts to `shared/alerts.json`

**Sample Alert:**
```json
{
  "event_type": "LOW_STOCK",
  "product_name": "Purple Label Cashmere Overcoat",
  "customer_name": "Michael Thompson",
  "customer_tier": "Platinum",
  "match_score": 120,
  "urgency": "HIGH",
  "outreach_message": "The Purple Label cashmere overcoat you admired last season is down to just two pieces in your size. I've noted your interest — worth a look before it's gone.",
  "price": 4995,
  "stock_level": 2
}
```

### 3. Monitoring Stack
- **Prometheus** scrapes metrics from monitor service every 15s
- **Grafana** visualizes:
  - Total events detected
  - Worker health status
  - Products being monitored
  - System performance

---

## Key Metrics

Available at `http://YOUR_VM_IP:9090/metrics`:

- `envoy_events_detected_total{event_type}` — Events by type
- `envoy_worker_status{worker_name}` — Worker health (1=healthy, 0=error)
- `envoy_products_monitored` — Active product count
- `envoy_scan_duration_seconds` — Performance per category

---

## Demo Notes

**For Presentation:**
1. Show Grafana dashboard with live metrics
2. Demo `cat shared/alerts.json` to show generated alerts
3. Show `docker ps` to demonstrate containerization
4. Explain customer matching algorithm with scoring breakdown
5. Connect to Ralph Lauren job descriptions (Web Ops + Client Development)

**Fallback Messages:**
If API credits run out, the system automatically uses template-based fallback messages. The matching logic and system architecture remain fully functional.

---

## Career Connection

This project maps directly to two Ralph Lauren roles:

**Web Operations Associate:**
- "Troubleshoot system issues" → Prometheus monitoring + worker health tracking
- "Manage platforms across channels" → Docker orchestration
- "Process improvement initiatives" → Automated event detection pipeline

**Client Development Lead:**
- "Leverage customer segmentation" → RFM-style scoring algorithm
- "Drive client outreach strategy" → AI-generated personalized messaging
- "Oversee clienteling platforms" → Alert generation system

---

## Future Enhancements

- Add size/color matching to customer profiles
- Implement actual web scraping for live inventory
- Add SMS/email notification layer
- Build admin UI for alert management
- Expand to multi-brand support
- Add A/B testing for outreach message effectiveness

---

## Acknowledgments

Built for CS Operating Systems final project, Spring 2025.  
Inspired by real clienteling workflows at luxury fashion brands.

---

## License

MIT License - Educational project for academic use.

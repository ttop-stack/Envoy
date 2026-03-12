#!/usr/bin/env python3
"""
Envoy Alert Engine - Matches scarcity events to customers and generates personalized outreach
"""

import json
import time
import os
from datetime import datetime
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
# ══════════════════════════════════════════════════════════════
# SECTION 1: CONFIG & SETUP
# ══════════════════════════════════════════════════════════════

DATA_DIR = Path("/data")
SHARED_DIR = Path("/shared")
CUSTOMERS_FILE = DATA_DIR / "mock_customers.json"
EVENTS_FILE = SHARED_DIR / "events.json"
ALERTS_FILE = SHARED_DIR / "alerts.json"
PROCESSED_EVENTS_FILE = SHARED_DIR / "processed_events.json"
SCAN_INTERVAL = 60  # seconds between checks for new events

# Initialize OpenAI client
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ══════════════════════════════════════════════════════════════
# SECTION 2: DATA LOADING
# ══════════════════════════════════════════════════════════════

def load_customers():
    """Load customer profiles from JSON"""
    try:
        with open(CUSTOMERS_FILE, 'r') as f:
            data = json.load(f)
        return data['customers']
    except Exception as e:
        print(f"[ERROR] Failed to load customers: {e}")
        return []


def load_events():
    """Load unprocessed events from JSON"""
    if not EVENTS_FILE.exists():
        return []
    
    try:
        with open(EVENTS_FILE, 'r') as f:
            events = json.load(f)
        
        # Load list of already processed event IDs
        processed_ids = set()
        if PROCESSED_EVENTS_FILE.exists():
            with open(PROCESSED_EVENTS_FILE, 'r') as f:
                processed_ids = set(json.load(f))
        
        # Filter to only new events
        new_events = []
        for event in events:
            event_id = f"{event['product_id']}_{event['timestamp']}"
            if event_id not in processed_ids:
                event['event_id'] = event_id
                new_events.append(event)
        
        return new_events
    
    except Exception as e:
        print(f"[ERROR] Failed to load events: {e}")
        return []


def mark_events_processed(event_ids):
    """Mark events as processed so we don't handle them again"""
    try:
        processed_ids = set()
        if PROCESSED_EVENTS_FILE.exists():
            with open(PROCESSED_EVENTS_FILE, 'r') as f:
                processed_ids = set(json.load(f))
        
        processed_ids.update(event_ids)
        
        with open(PROCESSED_EVENTS_FILE, 'w') as f:
            json.dump(list(processed_ids), f, indent=2)
    
    except Exception as e:
        print(f"[ERROR] Failed to mark events processed: {e}")


# ══════════════════════════════════════════════════════════════
# SECTION 3: CUSTOMER MATCHING & SCORING
# ══════════════════════════════════════════════════════════════

def match_customers_to_event(event, customers):
    """
    Find customers who would be interested in this product event
    Returns list of (customer, score) tuples sorted by relevance
    """
    matches = []
    
    for customer in customers:
        score = calculate_match_score(event, customer)
        if score > 0:
            matches.append((customer, score))
    
    # Sort by score descending, return top 3
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches[:3]


def calculate_match_score(event, customer):
    """
    Score how relevant this event is to this customer
    Higher score = better match
    """
    score = 0
    
    # Category match (most important)
    event_category = event['category']
    for pref_cat in customer.get('preferred_categories', []):
        if event_category in pref_cat:
            score += 50
            break
    
    # Price range match
    product_price = event['price']
    price_range = customer.get('preferred_price_range', [0, 999999])
    if price_range[0] <= product_price <= price_range[1]:
        score += 30
    
    # Engagement status bonus
    engagement = customer.get('engagement_status', '')
    if engagement == 'Highly Active':
        score += 20
    elif engagement == 'Active':
        score += 10
    elif engagement == 'At Risk':
        score += 15  # Good reactivation opportunity
    
    # Urgency multiplier
    urgency = event.get('urgency', 'MEDIUM')
    if urgency == 'CRITICAL':
        score = int(score * 1.5)
    elif urgency == 'HIGH':
        score = int(score * 1.2)
    
    return score


# ══════════════════════════════════════════════════════════════
# SECTION 4: LLM ALERT GENERATION
# ══════════════════════════════════════════════════════════════

def generate_outreach_message(event, customer):
    """
    Using claude to generate a personalized client outreach message
    """
    
    # Build context for the LLM
    product_name = event['product_name']
    event_type = event['event_type']
    urgency = event.get('urgency', 'MEDIUM')
    price = event['price']
    stock_level = event.get('stock_level', 'N/A')
    
    customer_name = customer['name']
    tier = customer['tier']
    avg_spend = customer['avg_spend']
    days_since = customer.get('days_since_purchase', 'unknown')
    
    # Different prompts for different event types
    if event_type == 'RESTOCK':
        context = f"A {product_name} just restocked after selling out. It historically sells out in {event.get('sell_velocity_days', 'N/A')} days. Only {stock_level} units available."
    elif event_type == 'LOW_STOCK':
        context = f"A {product_name} is running low on inventory. Only {stock_level} units remaining at ${price:,}."
    elif event_type == 'SOLD_OUT':
        context = f"A {product_name} just sold out at ${price:,}. This is a waiting list notification opportunity."
    else:
        context = f"Product event for {product_name}."
    
    prompt = f"""You are a luxury fashion client advisor at Ralph Lauren writing a personal outreach message to a VIP client.

Client Profile:
- Name: {customer_name}
- Tier: {tier}
- Average Spend: ${avg_spend:,}
- Days Since Last Purchase: {days_since}

Product Event:
{context}

Write a brief, elegant outreach message (2-3 sentences max) that:
- Feels personal and handwritten, not automated
- Creates urgency without being pushy
- Positions this as exclusive early access
- Suggests a next action (reserve, visit, call back)

Do not use a greeting or signature. Just the message body."""

    try:
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=150,
            temperature=0.7,
            system="You are a luxury brand client advisor crafting personalized VIP outreach.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        message = response.content[0].text.strip()
        return message        
    except Exception as e:
        print(f"[ERROR] OpenAI API call failed: {e}")
        return f"[FALLBACK] Hi {customer_name}, the {product_name} you've shown interest in is now available. Let me know if you'd like me to reserve one for you."


# ══════════════════════════════════════════════════════════════
# SECTION 5: ALERT LOGGING
# ══════════════════════════════════════════════════════════════

def save_alert(alert):
    """Append generated alert to alerts file"""
    try:
        if ALERTS_FILE.exists():
            with open(ALERTS_FILE, 'r') as f:
                alerts = json.load(f)
        else:
            alerts = []
        
        alert['generated_at'] = datetime.now().isoformat()
        alerts.append(alert)
        
        with open(ALERTS_FILE, 'w') as f:
            json.dump(alerts, f, indent=2)
        
        print(f"[ALERT] {alert['event_type']} → {alert['customer_name']} (Score: {alert['match_score']})")
    
    except Exception as e:
        print(f"[ERROR] Failed to save alert: {e}")


# ══════════════════════════════════════════════════════════════
# SECTION 6: MAIN PROCESSING LOOP
# ══════════════════════════════════════════════════════════════

def process_events():
    """Main processing function - runs once per cycle"""
    
    # Load data
    events = load_events()
    if not events:
        print("[INFO] No new events to process")
        return
    
    customers = load_customers()
    if not customers:
        print("[ERROR] No customers loaded, skipping processing")
        return
    
    print(f"[PROCESSING] {len(events)} new events...")
    
    processed_event_ids = []
    alerts_generated = 0
    
    # Process each event
    for event in events:
        # Find matching customers
        matches = match_customers_to_event(event, customers)
        
        if not matches:
            print(f"[SKIP] No customer match for {event['product_name']}")
            processed_event_ids.append(event['event_id'])
            continue
        
        # Generate alert for top match only (to avoid spam)
        customer, score = matches[0]
        
        # Generate personalized message via LLM
        message = generate_outreach_message(event, customer)
        
        # Create alert record
        alert = {
            'event_id': event['event_id'],
            'event_type': event['event_type'],
            'product_id': event['product_id'],
            'product_name': event['product_name'],
            'customer_id': customer['id'],
            'customer_name': customer['name'],
            'customer_tier': customer['tier'],
            'match_score': score,
            'urgency': event.get('urgency', 'MEDIUM'),
            'outreach_message': message,
            'price': event['price'],
            'stock_level': event.get('stock_level', 'N/A')
        }
        
        save_alert(alert)
        alerts_generated += 1
        processed_event_ids.append(event['event_id'])
        
        # Rate limiting - don't hammer the API
        time.sleep(1)
    
    # Mark events as processed
    mark_events_processed(processed_event_ids)
    print(f"[COMPLETE] Generated {alerts_generated} alerts from {len(events)} events\n")


# ══════════════════════════════════════════════════════════════
# SECTION 7: MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("[ENVOY ALERT ENGINE] Starting...")
    
     # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("[ERROR] ANTHROPIC_API_KEY environment variable not set")
        print("[ERROR] Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        exit(1)
    
    print(f"[INFO] Scanning for new events every {SCAN_INTERVAL}s")
    print("[INFO] Press Ctrl+C to stop\n")
    
    # Main loop
    try:
        while True:
            process_events()
            time.sleep(SCAN_INTERVAL)
    
    except KeyboardInterrupt:
        print("\n[ENVOY ALERT ENGINE] Shutting down...")

#!/usr/bin/env python3
"""
Envoy Monitor - Multi-threaded product availability monitor
Detects scarcity events and writes to shared event log
"""

import json
import time
import threading
from datetime import datetime
from pathlib import Path
from prometheus_client import start_http_server, Counter, Gauge, Summary

# ══════════════════════════════════════════════════════════════
# SECTION 1: CONFIG & SETUP
# ══════════════════════════════════════════════════════════════

DATA_DIR = Path("/data")
SHARED_DIR = Path("/shared")
PRODUCTS_FILE = DATA_DIR / "mock_products.json"
EVENTS_FILE = SHARED_DIR / "events.json"
SCAN_INTERVAL = 30  # seconds between scans

# ══════════════════════════════════════════════════════════════
# SECTION 2: PROMETHEUS METRICS
# ══════════════════════════════════════════════════════════════

EVENTS_DETECTED = Counter('envoy_events_detected_total', 'Total scarcity events detected', ['event_type'])
PRODUCTS_MONITORED = Gauge('envoy_products_monitored', 'Number of products being monitored')
WORKER_STATUS = Gauge('envoy_worker_status', 'Worker health status (1=healthy, 0=error)', ['worker_name'])
SCAN_DURATION = Summary('envoy_scan_duration_seconds', 'Time spent scanning products', ['category'])

# ══════════════════════════════════════════════════════════════
# SECTION 3: HELPER FUNCTIONS (Beginning 2/19--added load_ products
# with error handling, began log_event- needs to be checked before next )
# ══════════════════════════════════════════════════════════════

def load_products():
    """
    Load product catalog from JSON file
    
    Returns:
        list: List of product dictionaries from mock_products.json
    
    
    """
    with open(PRODUCTS_FILE), 'r') as f:
	data =json.load(f)
    return data['products']
except FileNotFoundError:
	print(f"[ERROR] Product file not found: {PRODUCTS_FILE}")
	return []
except json.JSONDecodeError as e:
	print(f"[ERROR] Invalid JSON in product file: {e}")
	return []
except KeyError:
	print(f"[ERROR] 'products' key not found in JSON")
	return []
    pass


def log_event(event):
    """
    Append a scarcity event to the shared events log
    
    Args:
        event (dict): Event dictionary with keys like event_type, product_name, etc.
    
    TODO:
    - Check if EVENTS_FILE exists, if so load existing events, else start with empty list
    - Add a 'timestamp' field to the event dict (use datetime.now().isoformat())
    - Append the event to the list
    - Write the full list back to EVENTS_FILE as JSON (with indent=2 for readability)
    - Print a message like: [EVENT] LOW_STOCK: Purple Label Coat (Stock: 2)
    - Increment the Prometheus counter: EVENTS_DETECTED.labels(event_type=event['event_type']).inc()
    - Handle any file errors gracefully
    """
    if EVENTS_FILE.exists():
	with open(EVENTS_FILE, 'r') as f:
		events = json.load(f)
   else:
	events = []
   
   event['timestamp'] = datetime.now().isoformat()

   events.append(event)

   with open(EVENTS_FILE, 'w') as f:
	json.dump(events,f,indent=2)
  
  print(f"[EVENT] {event['event_type']}: {event['product_name']}(Stock: {event.get('stock_level','N/A')})")

 EVENTS_DETECTED.labels(event_type=event['event_type']).inc()

    pass


def detect_scarcity_events(product, previous_stock=None):
    """
    Analyze a product and detect scarcity events
    
    Args:
        product (dict): Product dictionary with stock_level, stock_threshold, etc.
        previous_stock (int or None): Stock level from last scan, None if first scan
    
    Returns:
        list: List of event dictionaries (can be empty if no events detected)
    
    Event types to detect:
    1. LOW_STOCK: stock_level > 0 and stock_level <= stock_threshold
       - Include: event_type, product_id, product_name, category, stock_level, threshold, price
       - Set urgency to 'HIGH' if stock <= 2, else 'MEDIUM'
    
    2. SOLD_OUT: stock_level == 0 and previous_stock > 0
       - Include: event_type, product_id, product_name, category, stock_level, price
       - Set urgency to 'CRITICAL'
    
    3. RESTOCK: stock_level > 0 and previous_stock == 0
       - Include: event_type, product_id, product_name, category, stock_level, price, sell_velocity_days
       - Set urgency to 'CRITICAL' if sell_velocity_days < 10, else 'HIGH'
    
    TODO: Implement the three detection rules above and return a list of event dicts
    """
    # YOUR CODE HERE
    pass


# ══════════════════════════════════════════════════════════════
# SECTION 4: WORKER THREAD CLASS
# ══════════════════════════════════════════════════════════════

class MonitorWorker(threading.Thread):
    """Worker thread that monitors products in a specific category"""
    
    def __init__(self, name, category_filter):
        super().__init__(name=name, daemon=True)
        self.category_filter = category_filter
        self.running = True
        self.stock_memory = {}  # Track previous stock levels by product_id
        
    def run(self):
        """Main worker loop"""
        print(f"[WORKER] {self.name} started monitoring {self.category_filter}")
        WORKER_STATUS.labels(worker_name=self.name).set(1)
        
        while self.running:
            try:
                with SCAN_DURATION.labels(category=self.category_filter).time():
                    # Load all products
                    products = load_products()
                    
                    # Filter to this worker's category
                    filtered = [p for p in products if self.category_filter in p['category']]
                    PRODUCTS_MONITORED.set(len(filtered))
                    
                    # Check each product for scarcity events
                    for product in filtered:
                        product_id = product['id']
                        current_stock = product['stock_level']
                        previous_stock = self.stock_memory.get(product_id)
                        
                        # Detect events
                        events = detect_scarcity_events(product, previous_stock)
                        
                        # Log any events found
                        for event in events:
                            log_event(event)
                        
                        # Update memory
                        self.stock_memory[product_id] = current_stock
                
                WORKER_STATUS.labels(worker_name=self.name).set(1)
                
            except Exception as e:
                print(f"[ERROR] {self.name} encountered error: {e}")
                WORKER_STATUS.labels(worker_name=self.name).set(0)
            
            # Sleep before next scan
            time.sleep(SCAN_INTERVAL)
    
    def stop(self):
        """Gracefully stop the worker"""
        self.running = False


# ══════════════════════════════════════════════════════════════
# SECTION 5: MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("[ENVOY] Starting Monitor...")
    
    # Start Prometheus metrics server
    start_http_server(8000)
    print("[METRICS] Prometheus endpoint running on :8000/metrics")
    
    # Create worker threads for each category
    workers = [
        MonitorWorker("Apparel-Worker", "Apparel"),
        MonitorWorker("Accessories-Worker", "Accessories"),
        MonitorWorker("Home-Worker", "Home"),
    ]
    
    # Start all workers
    for worker in workers:
        worker.start()
    
    print(f"[ENVOY] {len(workers)} workers started. Scanning every {SCAN_INTERVAL}s...")
    print("[ENVOY] Press Ctrl+C to stop")
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[ENVOY] Shutting down...")
        for worker in workers:
            worker.stop()
        print("[ENVOY] Stopped.")

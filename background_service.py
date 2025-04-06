#!/usr/bin/env python3

import time
import threading
import queue
import json
import os
import datetime
from typing import Dict, Any, List, Optional
from enhanced_sms_parser import run_end_to_end
import db

# Global queue for SMS messages
sms_queue = queue.Queue()

# Flag to control the service
running = False

# Lock for thread-safe operations
lock = threading.Lock()

# In-memory store for processed SMS to avoid duplicates
processed_sms_hashes = set()

def hash_sms(sms_text: str) -> str:
    """
    Create a simple hash of SMS text to avoid duplicate processing
    
    Args:
        sms_text: The SMS text
        
    Returns:
        A hash of the SMS text
    """
    import hashlib
    return hashlib.md5(sms_text.encode('utf-8')).hexdigest()

def enqueue_sms(sms_text: str) -> bool:
    """
    Add an SMS to the processing queue if it hasn't been processed already
    
    Args:
        sms_text: The SMS text to process
        
    Returns:
        True if SMS was added to queue, False if it was a duplicate
    """
    # Create a hash of the SMS
    sms_hash = hash_sms(sms_text)
    
    with lock:
        # Check if we've already processed this SMS
        if sms_hash in processed_sms_hashes:
            print(f"[INFO] Duplicate SMS detected, skipping: {sms_text[:30]}...")
            return False
        
        # Add to queue and mark as processed
        sms_queue.put(sms_text)
        processed_sms_hashes.add(sms_hash)
        
        print(f"[INFO] SMS enqueued: {sms_text[:30]}...")
        return True

def sms_processor_thread():
    """
    Background thread that processes SMS messages from the queue
    """
    global running
    
    print("[INFO] SMS processor thread started")
    
    while running:
        try:
            # Get an SMS from the queue with a timeout (to allow checking the running flag)
            try:
                sms_text = sms_queue.get(block=True, timeout=1.0)
            except queue.Empty:
                # No SMS in queue, just continue the loop
                continue
            
            print(f"[INFO] Processing SMS: {sms_text[:30]}...")
            
            # Process the SMS
            try:
                start_time = time.time()
                result = run_end_to_end(sms_text)
                processing_time = time.time() - start_time
                
                print(f"[INFO] SMS processed in {processing_time:.2f}s")
                
                # Log the result
                if result.get("is_transaction", True):
                    print(f"[INFO] Transaction: {result['transaction']['amount']} {result['transaction']['transaction_type']}")
                    print(f"[INFO] Category: {result['category']}")
                    print(f"[INFO] Archetype: {result['archetype']}")
                else:
                    print(f"[INFO] Processed general question")
                
            except Exception as e:
                print(f"[ERROR] Error processing SMS: {e}")
            
            # Mark as done in the queue
            sms_queue.task_done()
            
        except Exception as e:
            print(f"[ERROR] Error in SMS processor thread: {e}")
    
    print("[INFO] SMS processor thread stopped")

def start_background_service():
    """
    Start the background SMS processing service
    """
    global running
    
    if running:
        print("[INFO] Background service is already running")
        return
    
    with lock:
        running = True
    
    # Start the processor thread
    processor = threading.Thread(target=sms_processor_thread)
    processor.daemon = True
    processor.start()
    
    print("[INFO] Background service started")
    return processor

def stop_background_service():
    """
    Stop the background SMS processing service
    """
    global running
    
    with lock:
        running = False
    
    print("[INFO] Background service stopping...")

def get_queue_status():
    """
    Get the current status of the SMS processing queue
    
    Returns:
        Dictionary with queue status information
    """
    return {
        "queue_size": sms_queue.qsize(),
        "processed_count": len(processed_sms_hashes),
        "is_running": running
    }

def simulate_incoming_sms(sms_text: str):
    """
    Simulate receiving an SMS in real-time
    
    Args:
        sms_text: The SMS text to process
    
    Returns:
        True if SMS was enqueued, False otherwise
    """
    # Add to queue
    enqueued = enqueue_sms(sms_text)
    
    if enqueued:
        # In a real app, you might want to notify connected clients
        # that a new SMS was received (e.g., via websockets)
        print(f"[INFO] New SMS received and enqueued")
    
    return enqueued

def simulate_real_time_monitor():
    """
    Simulate a real-time monitoring service that would listen for incoming SMS
    This would be replaced by a real SMS monitoring service in a production app
    """
    import random
    
    # Sample transaction SMS templates
    sms_templates = [
        "Your card ending with {card} has been debited for Rs.{amount} at {merchant} on {date}. Available balance is Rs.{balance}.",
        "Rs.{amount} debited from your account ending {card} for purchase at {merchant} on {date}. Updated balance: Rs.{balance}",
        "Rs.{amount} credited to your account ending with {card} on {date}. Updated balance: Rs.{balance}. Ref: NEFT/IMPS/RTG{ref}.",
        "Your {merchant} subscription of Rs.{amount} has been charged to your {bank} Credit Card ending with {card} on {date}. Available balance: Rs.{balance}."
    ]
    
    # Sample merchants
    merchants = ["Amazon", "Swiggy", "Zomato", "Flipkart", "Netflix", "Uber", "Ola", "BigBasket", "DMart", "IRCTC", "PVR", "Myntra"]
    
    # Sample bank names
    banks = ["HDFC", "ICICI", "SBI", "Axis", "Kotak", "Citi"]
    
    # Generate a random SMS
    template = random.choice(sms_templates)
    
    # Generate random values
    values = {
        "card": f"{random.randint(1000, 9999)}",
        "amount": f"{random.randint(100, 10000)}",
        "merchant": random.choice(merchants),
        "date": (datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 7))).strftime("%d-%m-%Y"),
        "balance": f"{random.randint(10000, 100000)}",
        "bank": random.choice(banks),
        "ref": f"{random.randint(100000, 999999)}"
    }
    
    # Format the template
    sms = template.format(**values)
    
    # Simulate receiving the SMS
    return simulate_incoming_sms(sms)

def main():
    """
    Main function for testing the background service
    """
    print("=== SMS Background Processing Service ===\n")
    
    # Start the background service
    processor_thread = start_background_service()
    
    try:
        print("\nSimulating incoming SMS messages (press Ctrl+C to stop)...")
        
        # Simulate some initial SMS messages
        for _ in range(3):
            simulate_real_time_monitor()
            time.sleep(2)  # Wait for processing
        
        # Wait for user input or Ctrl+C
        while True:
            print("\nOptions:")
            print("1. Simulate incoming SMS")
            print("2. Show queue status")
            print("3. Simulate specific SMS (input your own)")
            print("4. Exit")
            
            choice = input("\nEnter choice (1-4): ")
            
            if choice == "1":
                # Simulate a random SMS
                simulate_real_time_monitor()
                time.sleep(1)  # Give it a moment to process
                
            elif choice == "2":
                # Show queue status
                status = get_queue_status()
                print(f"\nQueue Status:")
                print(f"Queue Size: {status['queue_size']}")
                print(f"Processed SMS Count: {status['processed_count']}")
                print(f"Service Running: {status['is_running']}")
                
            elif choice == "3":
                # Get user input for SMS
                sms_text = input("\nEnter SMS text: ")
                if sms_text.strip():
                    simulate_incoming_sms(sms_text)
                    time.sleep(1)  # Give it a moment to process
                
            elif choice == "4":
                # Exit
                print("Exiting...")
                break
            
            else:
                print("Invalid choice, please try again.")
    
    except KeyboardInterrupt:
        print("\nKeyboard interrupt detected. Shutting down...")
    
    finally:
        # Stop the background service
        stop_background_service()
        
        # Wait for the processor thread to finish
        processor_thread.join(timeout=5.0)
        
        print("Background service stopped.")

if __name__ == "__main__":
    main() 
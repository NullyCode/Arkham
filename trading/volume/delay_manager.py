import logging
import random
import time
import threading

class DelayManager:
    def __init__(self, min_delay, max_delay, delay_callback):
        self.logger = logging.getLogger(__name__)
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.current_delay = 0
        self.delay_callback = delay_callback
        self.is_running = True
        self.countdown_thread = None

    def get_random_delay(self):
        """Generate random delay within configured range"""
        self.current_delay = random.uniform(self.min_delay, self.max_delay)
        return self.current_delay

    def countdown(self):
        """Countdown timer that updates the UI"""
        while self.current_delay > 0 and self.is_running:
            self.delay_callback(self.current_delay)
            time.sleep(0.1)  # Update every 100ms
            self.current_delay = max(0, self.current_delay - 0.1)

    def start_countdown(self):
        """Start countdown in a separate thread"""
        self.countdown_thread = threading.Thread(target=self.countdown)
        self.countdown_thread.start()

    def stop(self):
        """Stop countdown"""
        self.is_running = False
        if self.countdown_thread and self.countdown_thread.is_alive():
            self.countdown_thread.join()
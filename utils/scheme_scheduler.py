"""
Scheduler for Government Schemes Web Scraping
Handles automatic and manual scraping with scheduling capabilities
"""

import threading
import time
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
import schedule
import os

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, timedelta):
            return str(obj)
        return super().default(obj)

class SchemeScheduler:
    """
    Manages scheduled and manual scraping of government schemes
    """
    
    def __init__(self, scraping_function: Callable, storage_manager, 
                 schedule_hour: int = 2, schedule_minute: int = 0):
        """
        Initialize the scheduler
        
        Args:
            scraping_function: Function to call for scraping schemes
            storage_manager: SchemeStorageManager instance
            schedule_hour: Hour of day to run scheduled scraping (0-23)
            schedule_minute: Minute of hour to run scheduled scraping (0-59)
        """
        self.scraping_function = scraping_function
        self.storage_manager = storage_manager
        self.schedule_hour = schedule_hour
        self.schedule_minute = schedule_minute
        
        self.is_running = False
        self.scheduler_thread = None
        self.last_scheduled_run = None
        self.last_manual_run = None
        self.current_status = "idle"  # idle, running, error
        self.last_error = None
        
        # Setup scheduled scraping
        self.setup_schedule()
    
    def setup_schedule(self):
        """Setup the daily scraping schedule"""
        try:
            # Clear any existing schedules
            schedule.clear()
            
            # Schedule daily scraping
            schedule.every().day.at(f"{self.schedule_hour:02d}:{self.schedule_minute:02d}").do(
                self._run_scheduled_scraping
            )
            
            logging.info(f"Scheduled daily scraping at {self.schedule_hour:02d}:{self.schedule_minute:02d}")
            
        except Exception as e:
            logging.error(f"Error setting up schedule: {e}")
    
    def start_scheduler(self):
        """Start the background scheduler thread"""
        if not self.is_running:
            self.is_running = True
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self.scheduler_thread.start()
            logging.info("Scheme scheduler started")
    
    def stop_scheduler(self):
        """Stop the background scheduler"""
        self.is_running = False
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        logging.info("Scheme scheduler stopped")
    
    def _scheduler_loop(self):
        """Main scheduler loop running in background thread"""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logging.error(f"Error in scheduler loop: {e}")
                self.last_error = str(e)
                self.current_status = "error"
                time.sleep(300)  # Wait 5 minutes before retrying
    
    def _run_scheduled_scraping(self):
        """Run scheduled scraping (called by scheduler)"""
        logging.info("Starting scheduled scheme scraping")
        self.current_status = "running"
        self.last_error = None
        
        try:
            # Run the scraping
            schemes = self.scraping_function()
            
            # Save to storage
            if schemes:
                stats = self.storage_manager.save_schemes(schemes, scraping_source="scheduled")
                logging.info(f"Scheduled scraping completed: {stats}")
            else:
                logging.warning("Scheduled scraping returned no schemes")
            
            self.last_scheduled_run = datetime.now()
            self.current_status = "idle"
            
        except Exception as e:
            logging.error(f"Error in scheduled scraping: {e}")
            self.last_error = str(e)
            self.current_status = "error"
            
            # Log the failed operation
            self.storage_manager.log_scraping_operation(
                status="failed",
                error_message=str(e),
                scraping_source="scheduled"
            )
    
    def run_manual_scraping(self) -> Dict[str, Any]:
        """
        Run manual scraping immediately
        Returns dict with scraping results
        """
        logging.info("Starting manual scheme scraping")
        self.current_status = "running"
        self.last_error = None
        
        result = {
            "success": False,
            "schemes_found": 0,
            "schemes_added": 0,
            "schemes_updated": 0,
            "error": None,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Run the scraping
            schemes = self.scraping_function()
            result["schemes_found"] = len(schemes) if schemes else 0
            
            # Save to storage
            if schemes:
                stats = self.storage_manager.save_schemes(schemes, scraping_source="manual")
                result["schemes_added"] = stats["added"]
                result["schemes_updated"] = stats["updated"]
                result["success"] = True
                logging.info(f"Manual scraping completed: {stats}")
            else:
                result["error"] = "No schemes found during scraping"
                logging.warning("Manual scraping returned no schemes")
            
            self.last_manual_run = datetime.now()
            self.current_status = "idle"
            
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Error in manual scraping: {error_msg}")
            self.last_error = error_msg
            self.current_status = "error"
            result["error"] = error_msg
            
            # Log the failed operation
            self.storage_manager.log_scraping_operation(
                status="failed",
                error_message=error_msg,
                scraping_source="manual"
            )
        
        return result
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status and statistics"""
        next_run = None
        try:
            next_job = schedule.next_run()
            if next_job:
                next_run = next_job.isoformat()
        except Exception as e:
            logging.warning(f"Error getting next scheduled run: {e}")
            pass
        
        # Ensure all datetime objects are properly serialized
        status = {
            "is_running": self.is_running,
            "current_status": self.current_status,
            "schedule_time": f"{self.schedule_hour:02d}:{self.schedule_minute:02d}",
            "next_scheduled_run": next_run,
            "last_scheduled_run": self.last_scheduled_run.isoformat() if self.last_scheduled_run else None,
            "last_manual_run": self.last_manual_run.isoformat() if self.last_manual_run else None,
            "last_error": self.last_error,
            "thread_alive": self.scheduler_thread.is_alive() if self.scheduler_thread else False
        }
        
        # Test JSON serialization to catch any issues early
        try:
            json.dumps(status, cls=DateTimeEncoder)
        except Exception as e:
            logging.error(f"JSON serialization error in scheduler status: {e}")
            # Return a safe fallback status
            return {
                "is_running": bool(self.is_running),
                "current_status": str(self.current_status),
                "schedule_time": f"{self.schedule_hour:02d}:{self.schedule_minute:02d}",
                "next_scheduled_run": None,
                "last_scheduled_run": None,
                "last_manual_run": None,
                "last_error": str(self.last_error) if self.last_error else None,
                "thread_alive": False
            }
        
        return status
    
    def update_schedule(self, hour: int, minute: int = 0):
        """Update the scheduled scraping time"""
        try:
            self.schedule_hour = hour
            self.schedule_minute = minute
            self.setup_schedule()
            logging.info(f"Updated schedule to {hour:02d}:{minute:02d}")
            return True
        except Exception as e:
            logging.error(f"Error updating schedule: {e}")
            return False
    
    def is_scraping_due(self) -> bool:
        """Check if scraping is due (more than 24 hours since last run)"""
        if not self.last_scheduled_run:
            return True
        
        time_since_last = datetime.now() - self.last_scheduled_run
        return time_since_last > timedelta(hours=24)
    
    def get_time_until_next_run(self) -> Optional[str]:
        """Get human-readable time until next scheduled run"""
        try:
            next_run = schedule.next_run()
            if next_run:
                time_diff = next_run - datetime.now()
                
                if time_diff.days > 0:
                    return f"{time_diff.days} day(s), {time_diff.seconds // 3600} hour(s)"
                elif time_diff.seconds > 3600:
                    return f"{time_diff.seconds // 3600} hour(s), {(time_diff.seconds % 3600) // 60} minute(s)"
                else:
                    return f"{time_diff.seconds // 60} minute(s)"
        except:
            pass
        
        return None

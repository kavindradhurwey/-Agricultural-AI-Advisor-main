"""
Advanced Policy Scraping Scheduler
Automated government scheme scraping with intelligent triggers
"""

try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    print("WARNING: 'schedule' module not found. Scheduler functionality will be limited.")
    SCHEDULE_AVAILABLE = False
    # Create a mock schedule module for fallback
    class MockSchedule:
        def every(self, *args): return self
        def hour(self, *args): return self
        def day(self, *args): return self
        def hours(self, *args): return self
        def minutes(self, *args): return self
        def at(self, *args): return self
        def do(self, *args): return self
        def tag(self, *args): return self
        def clear(self, *args): pass
        def run_pending(self): pass
        def __getattr__(self, name): return lambda *args, **kwargs: self
    schedule = MockSchedule()

import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import json
import os
from dataclasses import dataclass, asdict
from enum import Enum

class ScheduleFrequency(Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"

@dataclass
class ScheduleConfig:
    """Configuration for scheduled tasks"""
    task_id: str
    frequency: ScheduleFrequency
    time_of_day: str = "09:00"  # HH:MM format
    day_of_week: Optional[str] = None  # For weekly tasks
    day_of_month: Optional[int] = None  # For monthly tasks
    custom_interval: Optional[int] = None  # For custom intervals
    enabled: bool = True
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    retry_count: int = 3
    retry_delay: int = 300  # seconds

class PolicyScheduler:
    """Advanced scheduler for policy scraping and notifications"""
    
    def __init__(self, config_file: str = "data/scheduler_config.json"):
        self.config_file = config_file
        self.schedules: Dict[str, ScheduleConfig] = {}
        self.running = False
        self.scheduler_thread = None
        self.callbacks: Dict[str, Callable] = {}
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Load existing configuration
        self.load_config()
        
        # Default schedules
        self.setup_default_schedules()
    
    def setup_default_schedules(self):
        """Setup default scheduling tasks"""
        default_schedules = [
            ScheduleConfig(
                task_id="policy_scraping_daily",
                frequency=ScheduleFrequency.DAILY,
                time_of_day="08:00"
            ),
            ScheduleConfig(
                task_id="weather_alerts_check",
                frequency=ScheduleFrequency.HOURLY,
                custom_interval=6  # Every 6 hours
            ),
            ScheduleConfig(
                task_id="market_price_update",
                frequency=ScheduleFrequency.DAILY,
                time_of_day="10:00"
            ),
            ScheduleConfig(
                task_id="user_notification_digest",
                frequency=ScheduleFrequency.DAILY,
                time_of_day="18:00"
            ),
            ScheduleConfig(
                task_id="database_cleanup",
                frequency=ScheduleFrequency.WEEKLY,
                day_of_week="sunday",
                time_of_day="02:00"
            )
        ]
        
        for schedule_config in default_schedules:
            if schedule_config.task_id not in self.schedules:
                self.schedules[schedule_config.task_id] = schedule_config
        # Persist defaults if we added any
        self.save_config()
    
    def load_config(self):
        """Load scheduler configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    try:
                        config_data = json.load(f)
                    except json.JSONDecodeError as je:
                        # Backup corrupted file and start fresh
                        self.logger.error(f"Corrupted scheduler config JSON: {je}")
                        try:
                            backup_path = f"{self.config_file}.bak"
                            os.replace(self.config_file, backup_path)
                            self.logger.error(f"Backed up corrupted config to {backup_path}")
                        except Exception as be:
                            self.logger.error(f"Failed to backup corrupted config: {be}")
                        config_data = {}

                # Reconstruct dataclasses, converting frequency strings back to Enum
                for task_id, config in (config_data or {}).items():
                    freq = config.get('frequency')
                    if isinstance(freq, str):
                        try:
                            config['frequency'] = ScheduleFrequency(freq)
                        except Exception:
                            config['frequency'] = ScheduleFrequency.DAILY
                    self.schedules[task_id] = ScheduleConfig(**config)
                
                if self.schedules:
                    self.logger.info(f"Loaded {len(self.schedules)} scheduled tasks")
        except Exception as e:
            self.logger.error(f"Error loading scheduler config: {e}")
    
    def save_config(self):
        """Save scheduler configuration to file"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            config_data = {}
            for task_id, schedule_config in self.schedules.items():
                data = asdict(schedule_config)
                # Convert Enum to serializable value
                if isinstance(schedule_config.frequency, ScheduleFrequency):
                    data['frequency'] = schedule_config.frequency.value
                config_data[task_id] = data
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
                
            self.logger.info("Scheduler configuration saved")
        except Exception as e:
            self.logger.error(f"Error saving scheduler config: {e}")
    
    def register_callback(self, task_id: str, callback: Callable):
        """Register a callback function for a scheduled task"""
        self.callbacks[task_id] = callback
        self.logger.info(f"Registered callback for task: {task_id}")
    
    def add_schedule(self, schedule_config: ScheduleConfig):
        """Add a new scheduled task"""
        self.schedules[schedule_config.task_id] = schedule_config
        self.save_config()
        
        if self.running:
            self._setup_schedule(schedule_config)
        
        self.logger.info(f"Added schedule: {schedule_config.task_id}")
    
    def remove_schedule(self, task_id: str):
        """Remove a scheduled task"""
        if task_id in self.schedules:
            del self.schedules[task_id]
            self.save_config()
            
            # Clear from schedule library
            schedule.clear(task_id)
            
            self.logger.info(f"Removed schedule: {task_id}")
    
    def update_schedule(self, task_id: str, **kwargs):
        """Update an existing scheduled task"""
        if task_id in self.schedules:
            for key, value in kwargs.items():
                if hasattr(self.schedules[task_id], key):
                    setattr(self.schedules[task_id], key, value)
            
            self.save_config()
            
            # Reschedule if running
            if self.running:
                schedule.clear(task_id)
                self._setup_schedule(self.schedules[task_id])
            
            self.logger.info(f"Updated schedule: {task_id}")
    
    def _setup_schedule(self, schedule_config: ScheduleConfig):
        """Setup individual schedule with the schedule library"""
        if not schedule_config.enabled:
            return
        
        task_id = schedule_config.task_id
        
        def job_wrapper():
            self._execute_task(schedule_config)
        
        # Setup based on frequency
        if schedule_config.frequency == ScheduleFrequency.HOURLY:
            if schedule_config.custom_interval:
                schedule.every(schedule_config.custom_interval).hours.do(job_wrapper).tag(task_id)
            else:
                schedule.every().hour.do(job_wrapper).tag(task_id)
                
        elif schedule_config.frequency == ScheduleFrequency.DAILY:
            schedule.every().day.at(schedule_config.time_of_day).do(job_wrapper).tag(task_id)
            
        elif schedule_config.frequency == ScheduleFrequency.WEEKLY:
            day = schedule_config.day_of_week.lower()
            getattr(schedule.every(), day).at(schedule_config.time_of_day).do(job_wrapper).tag(task_id)
            
        elif schedule_config.frequency == ScheduleFrequency.MONTHLY:
            # Monthly scheduling (approximate - runs on specific day each month)
            schedule.every().day.at(schedule_config.time_of_day).do(
                lambda: self._monthly_check(schedule_config)
            ).tag(task_id)
            
        elif schedule_config.frequency == ScheduleFrequency.CUSTOM:
            if schedule_config.custom_interval:
                schedule.every(schedule_config.custom_interval).minutes.do(job_wrapper).tag(task_id)
        
        # Update next run time
        schedule_config.next_run = self._get_next_run_time(schedule_config)
        self.save_config()
    
    def _monthly_check(self, schedule_config: ScheduleConfig):
        """Check if it's time to run monthly task"""
        today = datetime.now().day
        if today == (schedule_config.day_of_month or 1):
            self._execute_task(schedule_config)
    
    def _execute_task(self, schedule_config: ScheduleConfig):
        """Execute a scheduled task with retry logic"""
        task_id = schedule_config.task_id
        
        for attempt in range(schedule_config.retry_count):
            try:
                self.logger.info(f"Executing task: {task_id} (attempt {attempt + 1})")
                
                # Update last run time
                schedule_config.last_run = datetime.now().isoformat()
                
                # Execute callback if registered
                if task_id in self.callbacks:
                    result = self.callbacks[task_id]()
                    
                    if result:
                        self.logger.info(f"Task completed successfully: {task_id}")
                        break
                    else:
                        raise Exception("Task returned False")
                else:
                    self.logger.warning(f"No callback registered for task: {task_id}")
                    break
                    
            except Exception as e:
                self.logger.error(f"Task failed: {task_id} - {e}")
                
                if attempt < schedule_config.retry_count - 1:
                    self.logger.info(f"Retrying in {schedule_config.retry_delay} seconds...")
                    time.sleep(schedule_config.retry_delay)
                else:
                    self.logger.error(f"Task failed after {schedule_config.retry_count} attempts: {task_id}")
        
        # Update next run time
        schedule_config.next_run = self._get_next_run_time(schedule_config)
        self.save_config()
    
    def _get_next_run_time(self, schedule_config: ScheduleConfig) -> str:
        """Calculate next run time for a schedule"""
        try:
            # This is a simplified calculation
            now = datetime.now()
            
            if schedule_config.frequency == ScheduleFrequency.HOURLY:
                if schedule_config.custom_interval:
                    next_run = now + timedelta(hours=schedule_config.custom_interval)
                else:
                    next_run = now + timedelta(hours=1)
                    
            elif schedule_config.frequency == ScheduleFrequency.DAILY:
                time_parts = schedule_config.time_of_day.split(':')
                next_run = now.replace(
                    hour=int(time_parts[0]), 
                    minute=int(time_parts[1]), 
                    second=0, 
                    microsecond=0
                )
                if next_run <= now:
                    next_run += timedelta(days=1)
                    
            elif schedule_config.frequency == ScheduleFrequency.WEEKLY:
                next_run = now + timedelta(days=7)
                
            elif schedule_config.frequency == ScheduleFrequency.MONTHLY:
                next_run = now + timedelta(days=30)
                
            else:
                next_run = now + timedelta(hours=1)
            
            return next_run.isoformat()
            
        except Exception as e:
            self.logger.error(f"Error calculating next run time: {e}")
            return (datetime.now() + timedelta(hours=1)).isoformat()
    
    def start(self):
        """Start the scheduler"""
        if not SCHEDULE_AVAILABLE:
            self.logger.warning("Schedule module not available. Scheduler will run in limited mode.")
            return
            
        if self.running:
            self.logger.warning("Scheduler is already running")
            return
        
        self.running = True
        
        # Setup all schedules
        for schedule_config in self.schedules.values():
            self._setup_schedule(schedule_config)
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        self.logger.info(f"Scheduler started with {len(self.schedules)} tasks")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        schedule.clear()
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        self.logger.info("Scheduler stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                self.logger.error(f"Scheduler error: {e}")
                time.sleep(60)
    
    def get_status(self) -> Dict:
        """Get scheduler status and statistics"""
        return {
            "running": self.running,
            "total_tasks": len(self.schedules),
            "enabled_tasks": len([s for s in self.schedules.values() if s.enabled]),
            "tasks": {
                task_id: {
                    "enabled": config.enabled,
                    "frequency": config.frequency.value,
                    "last_run": config.last_run,
                    "next_run": config.next_run
                }
                for task_id, config in self.schedules.items()
            }
        }
    
    def force_run_task(self, task_id: str) -> bool:
        """Force run a specific task immediately"""
        if task_id in self.schedules and task_id in self.callbacks:
            try:
                self.logger.info(f"Force running task: {task_id}")
                result = self.callbacks[task_id]()
                
                # Update last run time
                self.schedules[task_id].last_run = datetime.now().isoformat()
                self.save_config()
                
                return bool(result)
            except Exception as e:
                self.logger.error(f"Error force running task {task_id}: {e}")
                return False
        
        return False

# Global scheduler instance
policy_scheduler = PolicyScheduler()

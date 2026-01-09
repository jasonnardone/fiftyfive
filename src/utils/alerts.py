"""Alerting system for critical events"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger

from src.models.config import AlertsConfig


class AlertDispatcher:
    """Dispatches alerts to configured channels"""

    def __init__(self, config: AlertsConfig):
        """Initialize alert dispatcher

        Args:
            config: Alerting configuration
        """
        self.config = config
        self._queue = asyncio.Queue()
        self._running = False
        self._dispatch_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start dispatch loop"""
        if self._running:
            return
            
        self._running = True
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())
        logger.info("Alert dispatcher started")

    async def stop(self) -> None:
        """Stop dispatch loop"""
        self._running = False
        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass
        logger.info("Alert dispatcher stopped")

    async def send_alert(self, title: str, message: str, level: str = "INFO") -> None:
        """Queue alert for dispatch

        Args:
            title: Alert title
            message: Alert body
            level: Severity (INFO, WARNING, CRITICAL)
        """
        payload = {
            "title": title,
            "message": message,
            "level": level,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Log immediately
        if level == "CRITICAL":
            logger.critical(f"ALERT: {title} - {message}")
        elif level == "WARNING":
            logger.warning(f"ALERT: {title} - {message}")
        else:
            logger.info(f"ALERT: {title} - {message}")
            
        await self._queue.put(payload)

    async def _dispatch_loop(self) -> None:
        """Process alert queue"""
        while self._running:
            try:
                alert = await self._queue.get()
                
                # Dispatch to enabled channels
                tasks = []
                
                if self.config.terminal_enabled:
                    # Already logged in send_alert, but could add fancy terminal output here
                    pass
                    
                if self.config.slack_enabled:
                    tasks.append(self._send_slack(alert))
                    
                if self.config.email_enabled:
                    tasks.append(self._send_email(alert))
                    
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                    
                self._queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Alert dispatch error: {e}")

    async def _send_slack(self, alert: Dict[str, Any]) -> None:
        """Send alert to Slack (Placeholder)"""
        # TODO: Implement Slack webhook
        pass

    async def _send_email(self, alert: Dict[str, Any]) -> None:
        """Send alert via Email (Placeholder)"""
        # TODO: Implement SMTP
        pass

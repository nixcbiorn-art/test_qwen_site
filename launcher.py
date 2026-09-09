"""
Launcher for the Monitoring System.
Creates a system tray icon to control the background monitoring process.
Designed to be compiled into a single .exe using PyInstaller.
"""
import asyncio
import threading
import os
import sys
import logging

# Conditional import for GUI components (fails in headless environments)
GUI_AVAILABLE = False
try:
    # Only try to import pystray if we're likely on a system with GUI
    import os
    if os.name == 'nt' or os.name == 'mac' or os.environ.get('DISPLAY'):
        import pystray
        from pystray import Icon, MenuItem, DefaultMenuItemCollection
        from PIL import Image, ImageDraw
        GUI_AVAILABLE = True
except (ImportError, Exception):
    pass

# Import project modules
from async_monitor import run_async_monitoring

# Configure logging for production (file only)
log_dir = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'monitor.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
    ]
)
logger = logging.getLogger("Launcher")

class MonitorApp:
    def __init__(self):
        self.monitor_task = None
        self.loop = None
        self.thread = None
        self.is_running = False
        self.icon = None

    def start_monitoring(self):
        if self.is_running:
            logger.info("Monitoring is already running.")
            return
        
        self.is_running = True
        logger.info("Starting monitoring thread...")
        
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            try:
                self.monitor_task = self.loop.create_task(self._run_monitor())
                self.loop.run_until_complete(self.monitor_task)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
            finally:
                self.loop.close()

        self.thread = threading.Thread(target=run_loop, daemon=True)
        self.thread.start()

    async def _run_monitor(self):
        try:
            # Load config relative to the executable
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
                data_path = os.path.join(os.path.dirname(sys.executable), 'data')
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
                data_path = os.path.join(base_path, 'data')
            
            # Ensure data path exists
            os.makedirs(data_path, exist_ok=True)
            
            # Override config path if needed or rely on env vars
            # For simplicity, we assume settings.json is in the 'data' folder next to exe
            # The config module should handle loading from standard locations or env vars
            
            await run_async_monitoring()
        except Exception as e:
            logger.error(f"Monitoring task failed: {e}")
            self.is_running = False

    def stop_monitoring(self):
        if not self.is_running:
            return
        
        logger.info("Stopping monitoring...")
        self.is_running = False
        
        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
        
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            
        logger.info("Monitoring stopped.")

    def on_start(self, icon, item):
        self.start_monitoring()
        icon.notify("Monitoring Started", "The system is now checking endpoints.")

    def on_stop(self, icon, item):
        self.stop_monitoring()
        icon.notify("Monitoring Stopped", "Background checks have been paused.")

    def on_exit(self, icon, item):
        self.stop_monitoring()
        icon.stop()

    def setup_icon(self):
        if not GUI_AVAILABLE:
            logger.warning("GUI libraries not available. Running in console mode.")
            return None
            
        # Create a simple icon in memory if file not found
        image = Image.new('RGB', (64, 64), color=(73, 109, 137))
        d = ImageDraw.Draw(image)
        d.text((10, 20), "MON", fill=(255, 255, 255))
        
        menu = DefaultMenuItemCollection(
            MenuItem("Start Monitoring", self.on_start, default=True),
            MenuItem("Stop Monitoring", self.on_stop),
            MenuItem("Exit", self.on_exit)
        )

        self.icon = Icon("MonitorApp", image, "Market Monitor", menu)
        return self.icon

def main():
    logger.info("Application launched.")
    app = MonitorApp()
    
    # Start monitoring automatically on launch
    app.start_monitoring()
    
    if GUI_AVAILABLE:
        icon = app.setup_icon()
        if icon:
            icon.run()
    else:
        # Console mode fallback
        print("Monitoring started in background. Press Ctrl+C to stop.")
        try:
            while True:
                asyncio.get_event_loop().run_until_complete(asyncio.sleep(1))
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received.")
        finally:
            app.stop_monitoring()
            logger.info("Application exited.")

if __name__ == "__main__":
    main()

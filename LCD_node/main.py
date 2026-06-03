import asyncio, http.server, logging, logging.handlers, os, sys, threading
sys.path.insert(0, os.path.dirname(__file__))
import config
from utils.daemon_launcher import start_someipyd
from services.someip_subscriber import start_someip_subscriber
from services.websocket_server import start_websocket_server

def setup_logging():
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    def make_handler(filename):
        h = logging.handlers.RotatingFileHandler(os.path.join(log_dir, filename), maxBytes=5*1024*1024, backupCount=3)
        h.setFormatter(fmt); h.setLevel(logging.INFO); return h
    root = logging.getLogger()
    root.handlers.clear(); root.setLevel(logging.DEBUG)
    console = logging.StreamHandler(); console.setFormatter(fmt); console.setLevel(logging.WARNING); root.addHandler(console)
    root.addHandler(make_handler("lcd_node.log"))
    someip_logger = logging.getLogger("SOMEIP"); someip_logger.addHandler(make_handler("someip.log")); someip_logger.propagate = False
    for lib in ["someipy", "websockets"]:
        logging.getLogger(lib).setLevel(logging.ERROR); logging.getLogger(lib).propagate = False

def start_http_server():
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    os.chdir(static_dir)
    handler = http.server.SimpleHTTPRequestHandler
    handler.log_message = lambda *args: None
    server = http.server.HTTPServer(("0.0.0.0", config.HTTP_PORT), handler)
    logging.getLogger(__name__).warning(f"[HTTP] Dashboard at http://{config.LCD_IP}:{config.HTTP_PORT}/automotive_dashboard.html")
    server.serve_forever()

async def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.warning("=" * 50)
    logger.warning("  LCD NODE STARTING")
    logger.warning("=" * 50)
    start_someipyd(config.DAEMON_CONFIG)
    threading.Thread(target=start_http_server, daemon=True, name="http-server").start()
    await start_websocket_server(config.WS_STATE_PORT)
    await start_someip_subscriber(config)
    logger.warning("[LCD] Active — SOME/IP and WebSocket running")
    await asyncio.get_event_loop().create_future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.getLogger(__name__).warning("[LCD] Shutting down gracefully...")

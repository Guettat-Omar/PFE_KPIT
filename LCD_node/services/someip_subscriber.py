import asyncio, json, logging
from someipy import ServiceBuilder, ClientServiceInstance, Event, EventGroup, TransportLayerProtocol, connect_to_someipy_daemon
from services.websocket_server import broadcast

logger = logging.getLogger(__name__)
someip_log = logging.getLogger("SOMEIP")

async def start_someip_subscriber(config):
    vehicle_state_event = Event(id=config.EVENT_ID, protocol=TransportLayerProtocol.UDP)
    eventgroup = EventGroup(id=config.EVENTGROUP_ID, events=[vehicle_state_event])
    service = (ServiceBuilder().with_service_id(config.SERVICE_ID).with_major_version(1).with_eventgroup(eventgroup).build())

    logger.warning("[SOME/IP] Connecting to daemon...")
    daemon = await connect_to_someipy_daemon()

    client = ClientServiceInstance(
        daemon=daemon, service=service, instance_id=config.INSTANCE_ID,
        endpoint_ip=config.LCD_IP, endpoint_port=config.DATA_PORT,
    )

    def on_event(event_id: int, payload: bytes):
        if event_id != config.EVENT_ID:
            return
        try:
            state = json.loads(payload.decode('utf-8'))
            lights = state.get('lights', {})
            wins = state.get('windows', {})
            doors = state.get('doors', {})
            nodes = state.get('nodes', {})
            lgt = (f"{lights.get('low_beam',0)}{lights.get('high_beam',0)}"
                   f"{lights.get('parking',0)}{lights.get('front_fog',0)}"
                   f"{lights.get('rear_fog',0)}{lights.get('brake',0)}"
                   f"{lights.get('reverse',0)}")
            someip_log.info(
                f"RX | PWF={state.get('pwf_state')} | LGT={lgt} | "
                f"WIN={wins.get('w1',0)}{wins.get('w2',0)}{wins.get('w3',0)}{wins.get('w4',0)} | "
                f"DR fl:{doors.get('fl_open',0)} fr:{doors.get('fr_open',0)} "
                f"rl:{doors.get('rl_open',0)} rr:{doors.get('rr_open',0)} lck:{doors.get('locked',0)} | "
                f"BCM:{nodes.get('bcm','?')[:2]} LSN:{nodes.get('lsn','?')[:2]} WBP:{nodes.get('wbp','?')[:2]}"
            )
            asyncio.ensure_future(broadcast(state))
        except json.JSONDecodeError as e:
            logger.error(f"[SOME/IP] Bad payload: {e}")

    client.register_callback(on_event)
    client.subscribe_eventgroup(eventgroup, ttl_subscription_seconds=10)
    logger.warning(f"[SOME/IP] Subscribed to Service 0x{config.SERVICE_ID:04X} EventGroup 0x{config.EVENTGROUP_ID:04X}")

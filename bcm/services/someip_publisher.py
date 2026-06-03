import asyncio
import json
import logging
import threading

from someipy import (
    ServiceBuilder,      # builds the Service definition
    ServerServiceInstance,  # represents BCM as a server on the bus
    Event,               # one notification event
    EventGroup,          # group of events clients subscribe to
    TransportLayerProtocol,  # UDP or TCP — we use UDP
    connect_to_someipy_daemon,  # connects to someipyd process
)

logger = logging.getLogger(__name__)

# ── Service definition constants ──────────────────────────────────────────────
# These IDs are the "contract" between BCM and LCD.
# Both sides must use identical values — if BCM offers 0x1234
# and LCD looks for 0x1235, they never find each other.

SERVICE_ID    = 0x1234   # identifies the VehicleState service
INSTANCE_ID   = 0x0001   # first (and only) instance of this service
EVENT_ID      = 0x8001   # the vehicle state notification event
EVENTGROUP_ID = 0x0001   # the group LCD subscribes to

BCM_IP        = "10.20.0.41"   # this Pi's IP — daemon needs this
DATA_PORT     = 30499          # port for SOME/IP data (not SD — SD uses 30490)


class SomeIPPublisher:
    """
    Publishes vehicle state over real SOME/IP.
    Runs an asyncio event loop in a background thread so the
    BCM main loop (synchronous) can call publish() freely.
    """

    def __init__(self):
        self._server: ServerServiceInstance | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ready = threading.Event()  # signals when daemon is connected

    def start(self) -> None:
        """Start SOME/IP service in a background thread."""
        thread = threading.Thread(
            target=self._run_loop,
            name="someip-publisher",
            daemon=True   # dies automatically when main program exits
        )
        thread.start()
        # Wait until the daemon connection is established before returning.
        # This prevents main.py from calling publish() before we're ready.
        self._ready.wait(timeout=10)
        if not self._ready.is_set():
            logger.error("[SOME/IP] Daemon connection timed out. Is someipyd running?")

    def _run_loop(self) -> None:
        """Entry point for the background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        # run_until_complete runs _start_service() once to set everything up,
        # then run_forever() keeps the loop alive to process daemon messages.
        self._loop.run_until_complete(self._start_service())
        self._loop.run_forever()

    async def _start_service(self) -> None:
        """Connect to daemon and register the SOME/IP service."""

        # Step 1 — Build the service definition.
        # This is a data structure that describes what BCM offers.
        # Both BCM and LCD will build this exact same definition.
        vehicle_state_event = Event(
            id=EVENT_ID,
            protocol=TransportLayerProtocol.UDP
        )
        eventgroup = EventGroup(
            id=EVENTGROUP_ID,
            events=[vehicle_state_event]
        )
        service = (
            ServiceBuilder()
            .with_service_id(SERVICE_ID)
            .with_major_version(1)
            .with_eventgroup(eventgroup)
            .build()
        )

        # Step 2 — Connect to the local someipyd daemon.
        # The daemon is already running on this Pi.
        # connect_to_someipy_daemon() uses the default socket /tmp/someipyd.sock
        logger.info("[SOME/IP] Connecting to someipyd daemon...")
        daemon = await connect_to_someipy_daemon()

        # Step 3 — Create the server service instance.
        # This tells the daemon: "I am a server for this service,
        # I'm reachable at BCM_IP:DATA_PORT, offer me every 2 seconds."
        self._server = ServerServiceInstance(
            daemon=daemon,
            service=service,
            instance_id=INSTANCE_ID,
            endpoint_ip=BCM_IP,
            endpoint_port=DATA_PORT,
            ttl=5,                    # subscription lives 5 seconds without renewal
            cyclic_offer_delay_ms=2000  # OfferService sent every 2 seconds
        )

        # Step 4 — Start offering.
        # From this moment, someipyd starts sending OfferService to
        # 224.224.224.245:30490 every 2 seconds.
        # Any node that subscribes will start receiving events.
        await self._server.start_offer()
        logger.info(
            f"[SOME/IP] Offering Service 0x{SERVICE_ID:04X} "
            f"Instance 0x{INSTANCE_ID:04X} on {BCM_IP}:{DATA_PORT}"
        )

        # Signal the main thread that we're ready to publish
        self._ready.set()

    def publish(self, vehicle_state: dict) -> None:
        """
        Called from BCM main loop to publish vehicle state.
        Serializes the dict to JSON bytes and sends the SOME/IP event.
        This is the ONLY method main.py needs to call.
        """
        if self._server is None or self._loop is None:
            return

        try:
            # Serialize dict → JSON string → bytes
            payload = json.dumps(vehicle_state).encode('utf-8')

            # send_event() must run inside the asyncio loop.
            # call_soon_threadsafe() schedules it from our synchronous
            # main loop thread safely.
            self._loop.call_soon_threadsafe(
                self._server.send_event,
                EVENTGROUP_ID,
                EVENT_ID,
                payload
            )
        except Exception as e:
            logger.error(f"[SOME/IP] Publish failed: {e}")

    def stop(self) -> None:
        """Cleanly stop offering the service."""
        if self._server and self._loop:
            try:
                # run_coroutine_threadsafe submits the coroutine to the background
                # loop AND gives us a Future we can wait on from this thread.
                # This is the correct way to call async code from a sync thread.
                future = asyncio.run_coroutine_threadsafe(
                    self._server.stop_offer(),
                    self._loop
                )
                future.result(timeout=2.0)   # wait up to 2 seconds for StopOffer to send
            except Exception:
                pass   # if it fails, we're shutting down anyway

            # Stop the event loop so run_forever() exits,
            # letting the background thread terminate cleanly
            self._loop.call_soon_threadsafe(self._loop.stop)

        logger.info("[SOME/IP] Service stopped")
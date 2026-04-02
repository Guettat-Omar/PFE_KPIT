#!/bin/bash
# can_init.sh - Idempotent CAN interface initialization

if ip link show can0 | grep -q "UP"; then
    echo "CAN interface can0 is already UP. Skipping initialization."
else
    echo "Bringing up CAN interface can0..."
    # Adjust the bitrate if your project uses a different speed (e.g., 500000)
    sudo ip link set can0 type can bitrate 500000
    sudo ip link set up can0
    echo "CAN interface can0 initialized successfully."
fi

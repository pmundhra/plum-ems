"""ID generation utilities"""

import random
import time

import base58


def _generate_id() -> str:
    """
    Generates a transaction ID where:
    - First 13 positions are base58 encoded nanosecond timestamp
    - Last 4 positions are random numbers
    """
    # Get current time in nanoseconds
    timestamp_ns = int(time.time_ns())

    # Convert to base58
    base58_timestamp = base58.b58encode(timestamp_ns.to_bytes(8, 'big')).decode('ascii')

    # Ensure we have exactly 13 characters by padding with '0' if needed
    if len(base58_timestamp) < 13:
        base58_timestamp = base58_timestamp.ljust(13, '0')
    else:
        base58_timestamp = base58_timestamp[:13]

    # Generate 4 random digits
    random_digits = ''.join(str(random.randint(0, 9)) for _ in range(4))

    # Combine timestamp and random digits
    return f"{base58_timestamp}{random_digits}"

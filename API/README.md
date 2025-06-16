# ABB Robot Web Services API

A comprehensive Python library for interacting with ABB robot controllers via their REST API and WebSocket interfaces.

## Architecture

The API follows a modular architecture with clear separation of concerns:

### Core API Files

- `abb_robot.py` - Main class with service-specific classes for robot functionality
- `abb_base.py` - Base API handling HTTP requests and WebSocket connections
- `abb_robot_utils.py` - Utilities for IO signal handling, subscription management, and data processing

### Class Structure

```
ABBRobot
├── API (ABBRobotAPI)
│   ├── HTTP/WebSocket handling
│   └── Authentication
├── Panel (Panel)
├── User (User)
├── Controller (Controller)  
├── IO (IO)
│   └── IOSignalProcessor - Handles IO data processing
├── Vision (Vision)
├── RAPID (RAPID)
├── MotionSystem (MotionSystem)
├── SubscriptionHelper - For individual service subscriptions
└── SubscriptionManager - For combined multi-service subscriptions
```

## Subscription Features

The API provides two approaches for handling subscriptions:

### 1. Service-Specific Subscriptions

Each service class (IO, RAPID, Vision, etc.) provides methods to:
- Get initial values from resources
- Subscribe to changes to those resources
- Receive callbacks when changes occur

Example:
```python
# Get initial signal value and subscribe to changes
result = robot.io.get_signal_value_and_subscribe(signal_path, callback)
initial_value = result['initial_value']
subscription_id = result['subscription_id']
```

### 2. Combined Subscriptions (NEW)

The SubscriptionManager provides a centralized way to:
- Collect resources from multiple services
- Get initial values for all resources at once
- Create a single subscription for all resources
- Manage subscriptions through a centralized interface

Example:
```python
# Set up combined subscription
robot.setup_combined_subscription(
    collect_signals=True,
    collect_panel=True,
    collect_rapid=True,
    collect_motion=True,
    collect_vision=True,
    io_signals=['/rw/iosystem/signals/DO_1', '/rw/iosystem/signals/DI_1']
)

# Get initial values
initial_values = robot.get_initial_values()

# Create subscription
subscription_id = robot.subscribe_to_collected_resources()

# Unsubscribe all
robot.unsubscribe_all()
```

## Getting Started

To use the API:

```python
from API.abb_robot import ABBRobot

# Initialize robot
robot = ABBRobot(
    host='192.168.125.1',
    username='Default User',
    password='robotics'
)

# Connect to robot
robot.connect()

# Use API services
robot.io.get_signal_value('/rw/iosystem/signals/DO_1')
robot.panel.get_speed_ratio()
robot.rapid.get_execution_state()
robot.motion.get_error_state()
robot.vision.get_vision_info()

# Create subscriptions with initial values
robot.setup_combined_subscription(collect_signals=True, collect_panel=True)
initial_values = robot.get_initial_values()
subscription_id = robot.subscribe_to_collected_resources()

# Disconnect when done
robot.disconnect()
```

## Examples

For detailed examples, please see the `examples` directory:
- `subscription_example.py` - Individual service subscriptions
- `combined_subscription_example.py` - Combined multi-service subscriptions

## Running Tests

For information on running tests, see the `tests/README.md` file.
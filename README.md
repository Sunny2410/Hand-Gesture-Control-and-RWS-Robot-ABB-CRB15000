# ABB Robot Control System

A comprehensive PyQt5-based user interface for controlling ABB robots through Robot Web Services (RWS) interface with additional features like hand gesture recognition and ESP32 integration.

## Features

### Robot Control
- Modern tabbed interface with real-time robot updates
- Connection management with secure credential handling
- Robot panel controls (motors, operation mode, speed ratio)
- I/O signal monitoring and control with search functionality
- RAPID program execution and module management
- Motion control with jogging and position/joint targeting

### Vision System
- Real-time hand gesture detection and tracking
- MediaPipe integration for accurate hand tracking
- Camera feed processing and calibration
- Vision-based robot control options

### ESP32 Integration
- WebSocket-based communication with ESP32
- Real-time sensor data monitoring
- I/O signal control through ESP32

### Advanced Features
- EGM (Externally Guided Motion) support for low-latency control
- Comprehensive logging and diagnostics
- System status monitoring and error handling
- Multiple robot profile management

## EGM Integration

The application includes integration with ABB's Externally Guided Motion (EGM) feature through the EGM tab. This allows for real-time control of ABB robots with low latency using UDP communication.

### Prerequisites for EGM

1. Your ABB robot must have the EGM option installed.
2. Configure EGM on the robot controller:
   - RobotStudio > Configuration > Communication > Transmission Protocol
   - Add a new UDP protocol and set the port number (usually 6510)
   - Configure EGM settings on the robot

### Using the EGM Tab

1. Connect to the robot using the Connection tab first.
2. Navigate to the EGM tab.
3. Enter the UDP port to listen on (same as configured on the robot).
4. Click "Start EGM" to begin listening for EGM communication.
5. Once a connection is established:
   - The current joint positions will be displayed.
   - You can use either Joint Control or Cartesian Control to move the robot.
   
### RAPID Code Requirements

## Requirements

- Python 3.6+
- PyQt5
- Requests
- Pillow (for image processing)
- OpenCV (for vision features)

## Installation

1. Clone the repository:
```
git clone https://github.com/yourusername/abb-robot-control-ui.git
cd abb-robot-control-ui
```

2. Create a virtual environment:
```
python -m venv venv
```

3. Activate the virtual environment:
   - On Windows:
   ```
   venv\Scripts\activate
   ```
   - On macOS/Linux:
   ```
   source venv/bin/activate
   ```

4. Install dependencies:
```
pip install -r requirements.txt
```

## Usage

Run the application:
```
python main.py
```

## Project Structure

```
.
├── main.py                 # Application entry point
├── ui/                     # UI components
│   ├── main_window.py      # Main application window
│   ├── splash_screen.py    # Application splash screen
│   ├── resources/          # Static resources
│   │   └── style.qss       # Application stylesheet
│   ├── tabs/               # UI tabs
│   │   ├── connection_tab.py  # Connection management
│   │   ├── panel_tab.py    # Robot panel controls
│   │   ├── io_tab.py       # I/O signal monitoring
│   │   ├── rapid_tab.py    # RAPID program execution
│   │   ├── motion_tab.py   # Motion control
│   │   ├── vision_tab.py   # Vision system
│   │   └── system_tab.py   # System information
│   └── widgets/            # Reusable UI components
│       ├── log_widget.py   # Logging widget
│       └── status_widget.py # Status bar widget
└── requirements.txt        # Project dependencies
```

## License

MIT 

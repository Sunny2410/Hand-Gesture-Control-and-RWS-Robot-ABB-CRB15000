from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
                           QLabel, QLineEdit, QPushButton, QComboBox, 
                           QGroupBox, QCheckBox, QFrame, QGridLayout,
                           QDoubleSpinBox, QSlider, QTabWidget,
                           QSpinBox, QRadioButton, QButtonGroup, QMessageBox,
                           QTextEdit, QSplitter, QTableWidget, QHeaderView, QTableWidgetItem)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QIcon, QColor, QPixmap, QImage

import time
import numpy as np
import socket
import traceback
import threading
import os
import cv2
import sys

# Import EGM client
from abb_egm_pyclient.egm_client import EGMClient
from abb_egm_pyclient import DEFAULT_UDP_PORT
from abb_egm_pyclient.atomic_counter import AtomicCounter

# Import ESP32 socket client
from rws_io.esp32_socket import ESP32Socket

# Ensure the vision module can be imported
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))  # Go up two levels
if project_root not in sys.path:
    sys.path.append(project_root)

# Import hand detector from vision module
try:
    from vision.hand_detector import HandDetector
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False


class EGMWorker(QThread):
    """Worker thread for EGM communication"""
    position_update = pyqtSignal(dict)
    status_update = pyqtSignal(str)
    error = pyqtSignal(str)
    connected = pyqtSignal(bool)
    debug_update = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.egm_client = None
        self.port = DEFAULT_UDP_PORT
        self.socket = None
        self.last_position = None  # Store the last received position
        
        # Control flags for thread coordination
        self.is_sending = False
        self.use_position_feedback = True  # Auto-echo position
        
        # Control mode
        self.control_mode = "SLIDERS"  # "SLIDERS", "ESP32", "VISION"
        self.esp32_position = None
    def configure(self, port):
        """Configure the EGM client with the specified port"""
        self.port = port
        
    def set_control_mode(self, mode):
        """Set the control mode (SLIDERS, ESP32, VISION)"""
        self.control_mode = mode
        self.debug_update.emit(f"Control mode changed to: {mode}")
        
    def set_esp32_position(self, position):
        """Set the current ESP32 position data"""
        self.esp32_position = position
        
    def run(self):
        """Main thread loop for EGM communication"""
        self.running = True
        self.cartesian_target = None
        
        try:
            # Create EGM client with custom socket handling
            self.debug_update.emit("Creating socket on port " + str(self.port))
            
            # First try to create a completely new EGM client
            try:
                # Important: Create EGM client first WITHOUT providing a socket
                self.egm_client = EGMClient(port=self.port)
                
                # Reference the socket created by the client
                self.socket = self.egm_client.socket
                
                # Ensure the send_counter is properly initialized
                if not hasattr(self.egm_client, 'send_counter') or self.egm_client.send_counter is None:
                    self.egm_client.send_counter = AtomicCounter()
                
                self.debug_update.emit("EGM client created successfully with default socket")
                
            except OSError as e:
                self.debug_update.emit(f"Failed to create EGM client: {str(e)}")
                
                # If failed, try to create our own socket with more options
                try:
                    self.debug_update.emit("Attempting to create custom socket")
                    
                    # Close any existing socket
                    if self.socket:
                        try:
                            self.socket.close()
                        except:
                            pass
                        
                    # Wait for OS to release the socket
                    time.sleep(1)
                    
                    # Create a new socket
                    self.socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
                    self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    
                    # On Windows, we need SO_REUSEPORT as well if available
                    try:
                        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                        self.debug_update.emit("Added SO_REUSEPORT option")
                    except (AttributeError, OSError):
                        self.debug_update.emit("SO_REUSEPORT option not available")
                    
                    # Set socket timeout to non-blocking
                    self.socket.settimeout(0.5)
                    
                    # Try to bind the socket
                    self.socket.bind(('', self.port))
                    self.debug_update.emit("Custom socket bound successfully")
                    
                    # Create EGM client and replace its socket
                    self.egm_client = EGMClient(port=self.port)
                    self.egm_client.socket = self.socket
                    
                    # Ensure the send_counter is properly initialized
                    if not hasattr(self.egm_client, 'send_counter') or self.egm_client.send_counter is None:
                        self.egm_client.send_counter = AtomicCounter()
                        
                    self.debug_update.emit("EGM client created with custom socket")
                    
                except Exception as retry_e:
                    self.error.emit(f"Failed to bind socket: {str(retry_e)}")
                    self.debug_update.emit(f"Socket binding failed: {str(retry_e)}\n{traceback.format_exc()}")
                    self.running = False
                    return
            
            self.status_update.emit(f"Listening for EGM messages on port {self.port}")
            
            # Wait for first message to establish connection
            try:
                self.debug_update.emit("Waiting for initial EGM message...")
                pb_robot_msg = self.egm_client.receive_msg()
                self.connected.emit(True)
                self.status_update.emit("EGM connection established")
                self.debug_update.emit("Connection established with controller at " + 
                                     str(self.egm_client.robot_controller_address))
                
                # Extract initial cartesian position if available
                if hasattr(pb_robot_msg.feedBack, "cartesian") and pb_robot_msg.feedBack.cartesian.HasField("pos"):
                    pos = pb_robot_msg.feedBack.cartesian.pos
                    euler = pb_robot_msg.feedBack.cartesian.euler
                    cartesian_data = {
                        "x": pos.x, "y": pos.y, "z": pos.z,
                        "rx": euler.x, "ry": euler.y, "rz": euler.z
                    }
                    self.last_position = cartesian_data  # Store latest position
                    self.position_update.emit(cartesian_data)
                    self.debug_update.emit(f"Initial position: {cartesian_data}")
                    
                    # Send a reply with current position to maintain connection
                    self.send_cartesian_target(pos.x, pos.y, pos.z, euler.x, euler.y, euler.z)
                    self.debug_update.emit(f"Sent initial position: {cartesian_data}")
            except Exception as e:
                self.error.emit(f"Failed to receive initial EGM message: {str(e)}")
                self.debug_update.emit(f"Error receiving initial message: {str(e)}\n{traceback.format_exc()}")
                self.connected.emit(False)
                self.running = False
                return
            
            # Create separate threads for receiving and sending EGM messages
            receive_thread = threading.Thread(target=self.receive_loop, daemon=True)
            send_thread = threading.Thread(target=self.send_loop, daemon=True)
            
            receive_thread.start()
            send_thread.start()
            
            # Main thread just waits for termination
            while self.running:
                time.sleep(0.1)
                
            # Wait for threads to finish
            receive_thread.join(timeout=2.0)
            send_thread.join(timeout=2.0)
            
        except Exception as e:
            self.error.emit(f"Failed to initialize EGM client: {str(e)}")
            self.debug_update.emit(f"Initialization error: {str(e)}\n{traceback.format_exc()}")
            self.connected.emit(False)
        
        # Clean up resources
        try:
            if self.socket:
                self.debug_update.emit("Closing socket")
                self.socket.close()
                self.socket = None
            self.egm_client = None
        except Exception as e:
            self.debug_update.emit(f"Error closing socket: {str(e)}")
        
        self.running = False
        self.status_update.emit("EGM communication stopped")
        self.debug_update.emit("EGM thread stopped")
    
    def receive_loop(self):
        """Thread function to continuously receive messages from robot"""
        while self.running:
            try:
                # Receive message from robot
                pb_robot_msg = self.egm_client.receive_msg()
                
                # Extract cartesian position
                if hasattr(pb_robot_msg.feedBack, "cartesian") and pb_robot_msg.feedBack.cartesian.HasField("pos"):
                    pos = pb_robot_msg.feedBack.cartesian.pos
                    euler = pb_robot_msg.feedBack.cartesian.euler
                    cartesian_data = {
                        "x": pos.x, "y": pos.y, "z": pos.z,
                        "rx": euler.x, "ry": euler.y, "rz": euler.z
                    }
                    self.last_position = cartesian_data  # Store latest position
                    self.position_update.emit(cartesian_data)
                
                # Check convergence status
                if hasattr(pb_robot_msg, "mciConvergenceMet") and pb_robot_msg.mciConvergenceMet:
                    self.status_update.emit("Position converged")
                
            except Exception as e:
                if self.running:  # Only log errors if still running
                    self.debug_update.emit(f"Error receiving message: {str(e)}")
                time.sleep(0.5)  # Wait before retrying
    
    def send_loop(self):
        """Thread function to continuously send position updates based on active control mode"""
        last_send_time = 0
        
        while self.running:
            try:
                current_time = time.time()
                
                # Send command every 50ms (20Hz)
                if (current_time - last_send_time) >= 0.05:
                    
                    # Choose source based on control mode
                    if self.control_mode == "SLIDERS" and hasattr(self, "get_slider_values"):
                        # Get values from UI sliders
                        values = self.get_slider_values()
                        if values:
                            self.debug_update.emit(f"EGM sending: {values}")
                            self.egm_client.send_planned_frame(
                                values["x"], values["y"], values["z"],
                                values["rx"], values["ry"], values["rz"]
                            )
                            
                    elif self.control_mode == "ESP32" and self.esp32_position:
                        # Get values from ESP32 wrist controller
                        esp_pos = self.esp32_position
                        
                        # Calculate new position by adding ESP32 deltas to robot position
                        new_pos = {
                            "x":esp_pos["x"],
                            "y": esp_pos["y"],
                            "z": esp_pos["z"],
                            "rx": esp_pos["rx"],
                            "ry": esp_pos["ry"],
                            "rz": esp_pos["rz"]
                        }
                        
                        self.egm_client.send_planned_frame(
                            new_pos["x"], new_pos["y"], new_pos["z"],
                            new_pos["rx"], new_pos["ry"], new_pos["rz"]
                        )
                        self.debug_update.emit(f"EGM sending: {new_pos}")
                    # Add VISION mode here if needed
                    
                    last_send_time = current_time
                
                # Small delay to avoid excessive CPU usage
                time.sleep(0.01)
                
            except Exception as e:
                self.debug_update.emit(f"Error in send loop: {str(e)}")
                time.sleep(0.5)

    def stop(self):
        """Stop the worker thread"""
        self.debug_update.emit("Stopping EGM worker thread")
        self.running = False
        
        # Wait for thread to finish
        self.wait(2000)  # Wait up to 2 seconds
        
        # If thread didn't finish, force socket closure
        if self.socket:
            try:
                self.debug_update.emit("Forcing socket closure")
                # Force socket to unblock by shutting down properly
                try:
                    self.socket.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                self.socket.close()
                self.socket = None
            except Exception as e:
                self.debug_update.emit(f"Error forcing socket closure: {str(e)}")
        
        # Explicitly set client to None
        self.egm_client = None
    
    def send_cartesian_target(self, x, y, z, rx, ry, rz):
        """Send cartesian target to robot (now used only for initial positioning)"""
        if not self.egm_client:
            self.error.emit("EGM client not initialized")
            return False
        
        try:
            self.status_update.emit(f"Moving to cartesian target: [{x}, {y}, {z}, {rx}, {ry}, {rz}]")
            self.debug_update.emit(f"Sending cartesian target: x={x}, y={y}, z={z}, rx={rx}, ry={ry}, rz={rz}")
            
            # Send directly using EGM client
            self.egm_client.send_planned_frame(x, y, z, rx, ry, rz)
            
            # Send a second time for reliability
            time.sleep(0.05)
            self.egm_client.send_planned_frame(x, y, z, rx, ry, rz)
            
            return True
            
        except Exception as e:
            self.error.emit(f"Error sending cartesian target: {str(e)}")
            self.debug_update.emit(f"Error sending cartesian target: {str(e)}\n{traceback.format_exc()}")
            return False

    def reset_sequence_counter(self):
        """Reset the sequence counter to ensure fresh commands"""
        if not self.egm_client:
            return False
            
        try:
            # Use the EGMClient's native method to reset the counter
            if hasattr(self.egm_client, 'reset_sequence_counter'):
                self.egm_client.reset_sequence_counter()
            else:
                # Fallback if method not available
                self.egm_client.send_counter = AtomicCounter()
                
            self.debug_update.emit("EGM sequence counter reset")
            return True
            
        except Exception as e:
            self.debug_update.emit(f"Error resetting sequence counter: {str(e)}")
            return False
    
    def update_sliders_with_position(self, spinboxes, sliders):
        """Update UI sliders with current position if they don't have focus"""
        if not self.last_position:
            return
            
        # Only update if we have valid position data
        pos = self.last_position
        
        # Update X, Y, Z position
        self._update_if_not_focused(spinboxes['x'], sliders['x'], pos['x'])
        self._update_if_not_focused(spinboxes['y'], sliders['y'], pos['y'])
        self._update_if_not_focused(spinboxes['z'], sliders['z'], pos['z'])
        
        # Update orientation
        self._update_if_not_focused(spinboxes['rx'], sliders['rx'], pos['rx'])
        self._update_if_not_focused(spinboxes['ry'], sliders['ry'], pos['ry'])
        self._update_if_not_focused(spinboxes['rz'], sliders['rz'], pos['rz'])
    
    def _update_if_not_focused(self, spinbox, slider, value):
        """Update spinbox and slider if they don't have focus"""
        if not spinbox.hasFocus() and not slider.hasFocus():
            # Temporarily block signals to prevent feedback loops
            spinbox.blockSignals(True)
            slider.blockSignals(True)
            
            spinbox.setValue(value)
            slider.setValue(int(value))
            
            spinbox.blockSignals(False)
            slider.blockSignals(False)


class RobotControlTab(QTabWidget):
    """Tab for robot control combining EGM, Vision and ESP32"""
    
    def __init__(self):
        super().__init__()
        
        # Store robot reference
        self.robot = None
        
        # EGM worker
        self.egm_worker = EGMWorker()
        self.egm_worker.position_update.connect(self.update_cartesian_position)
        self.egm_worker.status_update.connect(self.update_status)
        self.egm_worker.error.connect(self.handle_error)
        self.egm_worker.connected.connect(self.update_connection_status)
        self.egm_worker.debug_update.connect(self.update_debug_log)
        
        # Pass the slider values method to the worker
        self.egm_worker.get_slider_values = self.get_slider_values
        
        # ESP32 socket worker
        self.esp32_worker = ESP32Socket()
        self.esp32_worker.wrist_data_received.connect(self.update_esp32_position)
        self.esp32_worker.status_update.connect(self.update_status)
        self.esp32_worker.error.connect(self.handle_error)
        self.esp32_worker.debug_update.connect(self.update_debug_log)
        
        # Camera and vision processing variables
        self.camera = None
        self.is_streaming = False
        self.processed_frame = None
        self.n_fingers = -1
        self.last_detected_gesture = "Không phát hiện tay"
        self.hand_option = -1
        
        # Initialize UI variables
        self.slider_initialized = False
        
        # Initialize HandDetector if MediaPipe is available
        if MEDIAPIPE_AVAILABLE:
            try:
                from vision.hand_detector import HandDetector
                self.hand_detector = HandDetector(min_detection_confidence=0.7)
                self.mediapipe_available = True
                print("Hand detector initialized successfully")
            except Exception as e:
                print(f"Failed to initialize hand detector: {str(e)}")
                traceback.print_exc()
                self.mediapipe_available = False
                self.hand_detector = None
        else:
            self.mediapipe_available = False
            self.hand_detector = None
            print("MediaPipe not available - hand detection disabled")
        
        # Initialize UI
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        # Create tabs
        self.control_tab = QWidget()
        self.settings_tab = QWidget()
        
        self.addTab(self.control_tab, "Robot Control")
        self.addTab(self.settings_tab, "Settings")
        
        self.setup_control_tab()
        self.setup_settings_tab()
        
    def setup_control_tab(self):
        """Setup the robot control tab"""
        # Main layout
        main_layout = QHBoxLayout(self.control_tab)
        
        # Left side - Camera view
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Camera controls
        camera_controls = QHBoxLayout()
        
        self.camera_combo = QComboBox()
        self.camera_combo.addItem("Camera 0")
        self.camera_combo.addItem("Camera 1")
        self.camera_combo.addItem("Camera 2")
        camera_controls.addWidget(self.camera_combo)
        
        self.connect_camera_button = QPushButton("Connect")
        self.connect_camera_button.clicked.connect(self.connect_camera)
        camera_controls.addWidget(self.connect_camera_button)
        
        self.disconnect_camera_button = QPushButton("Disconnect")
        self.disconnect_camera_button.clicked.connect(self.disconnect_camera)
        self.disconnect_camera_button.setEnabled(False)
        camera_controls.addWidget(self.disconnect_camera_button)
        
        self.start_stream_button = QPushButton("Start Stream")
        self.start_stream_button.clicked.connect(self.start_stream)
        self.start_stream_button.setEnabled(False)
        camera_controls.addWidget(self.start_stream_button)
        
        self.stop_stream_button = QPushButton("Stop Stream")
        self.stop_stream_button.clicked.connect(self.stop_stream)
        self.stop_stream_button.setEnabled(False)
        camera_controls.addWidget(self.stop_stream_button)
        
        left_layout.addLayout(camera_controls)
        
        # Camera view group
        camera_group = QGroupBox("Camera View")
        camera_layout = QVBoxLayout(camera_group)
        
        # Video feed - make it larger and more prominent
        self.video_label = QLabel("No video feed")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black; color: white;")
        self.video_label.setMinimumHeight(600)  # Increased height
        self.video_label.setMinimumWidth(800)   # Set minimum width
        camera_layout.addWidget(self.video_label)
        
        # Hand gesture info
        gesture_layout = QHBoxLayout()
        gesture_layout.addWidget(QLabel("Detected Gesture:"))
        self.gesture_label = QLabel("No hand detected")
        self.gesture_label.setStyleSheet("font-weight: bold; color: green;")
        gesture_layout.addWidget(self.gesture_label)
        
        gesture_layout.addWidget(QLabel("Fingers:"))
        self.fingers_label = QLabel("-1")
        self.fingers_label.setStyleSheet("font-weight: bold; color: blue;")
        gesture_layout.addWidget(self.fingers_label)
        
        gesture_layout.addWidget(QLabel("Tap:"))
        self.tap_label = QLabel("-1")
        self.tap_label.setStyleSheet("font-weight: bold; color: blue;")
        gesture_layout.addWidget(self.tap_label)
        
        # Add double tap status display
        gesture_layout.addWidget(QLabel("Double Tap:"))
        self.double_tap_status = QLabel("Not Active")
        self.double_tap_status.setStyleSheet("font-weight: bold; color: red;")
        gesture_layout.addWidget(self.double_tap_status)

        camera_layout.addLayout(gesture_layout)
        
        left_layout.addWidget(camera_group)
        
        # Right side - Control panels
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # EGM Connection group
        connection_group = QGroupBox("EGM Connection")
        connection_layout = QFormLayout(connection_group)
        
        # Connection buttons
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start EGM")
        self.start_button.clicked.connect(self.start_egm)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop EGM")
        self.stop_button.clicked.connect(self.stop_egm)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        connection_layout.addRow("", button_layout)
        
        # Status label
        self.status_label = QLabel("Not connected")
        self.status_label.setStyleSheet("font-weight: bold;")
        connection_layout.addRow("Status:", self.status_label)
        
        # Robot state label
        self.robot_state_label = QLabel("Unknown")
        self.robot_state_label.setStyleSheet("font-weight: bold;")
        connection_layout.addRow("Robot State:", self.robot_state_label)
        
        right_layout.addWidget(connection_group)
        
        # ESP32 connection group
        esp32_group = QGroupBox("ESP32 Wrist Controller")
        esp32_layout = QFormLayout(esp32_group)
        
        # ESP32 buttons
        esp32_button_layout = QHBoxLayout()
        
        self.connect_esp32_button = QPushButton("Connect ESP32")
        self.connect_esp32_button.clicked.connect(self.connect_esp32)
        esp32_button_layout.addWidget(self.connect_esp32_button)
        
        self.disconnect_esp32_button = QPushButton("Disconnect")
        self.disconnect_esp32_button.clicked.connect(self.disconnect_esp32)
        self.disconnect_esp32_button.setEnabled(False)
        esp32_button_layout.addWidget(self.disconnect_esp32_button)
        
        esp32_layout.addRow("", esp32_button_layout)
        
        # ESP32 status
        self.esp32_status_label = QLabel("Not connected")
        self.esp32_status_label.setStyleSheet("font-weight: bold;")
        esp32_layout.addRow("ESP32 Status:", self.esp32_status_label)
        
        # Control mode
        self.control_mode_combo = QComboBox()
        self.control_mode_combo.addItem("UI Sliders")
        self.control_mode_combo.addItem("ESP32 Wrist Control")
        self.control_mode_combo.currentIndexChanged.connect(self.change_control_mode)
        esp32_layout.addRow("Control Mode:", self.control_mode_combo)
        
        
        right_layout.addWidget(esp32_group)
        
        # Current position group
        current_position_group = QGroupBox("Current Robot Position")
        current_position_layout = QGridLayout(current_position_group)
        
        # Position labels - reorganized into 2 rows of 3 columns
        # Row 1: X, Y, Z
        current_position_layout.addWidget(QLabel("X:"), 0, 0)
        self.x_label = QLabel("0.0 mm")
        self.x_label.setStyleSheet("font-weight: bold;")
        current_position_layout.addWidget(self.x_label, 0, 1)
        
        current_position_layout.addWidget(QLabel("Y:"), 0, 2)
        self.y_label = QLabel("0.0 mm")
        self.y_label.setStyleSheet("font-weight: bold;")
        current_position_layout.addWidget(self.y_label, 0, 3)
        
        current_position_layout.addWidget(QLabel("Z:"), 0, 4)
        self.z_label = QLabel("0.0 mm")
        self.z_label.setStyleSheet("font-weight: bold;")
        current_position_layout.addWidget(self.z_label, 0, 5)
        
        # Row 2: Rx, Ry, Rz
        current_position_layout.addWidget(QLabel("Rx:"), 1, 0)
        self.rx_label = QLabel("0.0°")
        self.rx_label.setStyleSheet("font-weight: bold;")
        current_position_layout.addWidget(self.rx_label, 1, 1)
        
        current_position_layout.addWidget(QLabel("Ry:"), 1, 2)
        self.ry_label = QLabel("0.0°")
        self.ry_label.setStyleSheet("font-weight: bold;")
        current_position_layout.addWidget(self.ry_label, 1, 3)
        
        current_position_layout.addWidget(QLabel("Rz:"), 1, 4)
        self.rz_label = QLabel("0.0°")
        self.rz_label.setStyleSheet("font-weight: bold;")
        current_position_layout.addWidget(self.rz_label, 1, 5)
        
        right_layout.addWidget(current_position_group)
        
        # Target position group
        target_group = QGroupBox("Target Position Control")
        self.target_layout = QVBoxLayout(target_group)
        
        # Create slider control widgets (will be shown/hidden dynamically)
        self.slider_widget = QWidget()
        slider_layout = QGridLayout(self.slider_widget)
        
        # Position inputs with sliders
        slider_layout.addWidget(QLabel("X:"), 0, 0)
        self.x_spinbox = QDoubleSpinBox()
        self.x_spinbox.setRange(-2000, 2000)
        self.x_spinbox.setSuffix(" mm")
        self.x_spinbox.setSingleStep(10.0)
        self.x_spinbox.setDecimals(2)
        slider_layout.addWidget(self.x_spinbox, 0, 1)
        
        self.x_slider = QSlider(Qt.Horizontal)
        self.x_slider.setRange(-2000, 2000)
        self.x_slider.setSingleStep(1)
        self.x_slider.setPageStep(10)
        slider_layout.addWidget(self.x_slider, 0, 2)
        
        slider_layout.addWidget(QLabel("Y:"), 1, 0)
        self.y_spinbox = QDoubleSpinBox()
        self.y_spinbox.setRange(-2000, 2000)
        self.y_spinbox.setSuffix(" mm")
        self.y_spinbox.setSingleStep(10.0)
        self.y_spinbox.setDecimals(2)
        slider_layout.addWidget(self.y_spinbox, 1, 1)
        
        self.y_slider = QSlider(Qt.Horizontal)
        self.y_slider.setRange(-2000, 2000)
        self.y_slider.setSingleStep(1)
        self.y_slider.setPageStep(10)
        slider_layout.addWidget(self.y_slider, 1, 2)
        
        slider_layout.addWidget(QLabel("Z:"), 2, 0)
        self.z_spinbox = QDoubleSpinBox()
        self.z_spinbox.setRange(-2000, 2000)
        self.z_spinbox.setSuffix(" mm")
        self.z_spinbox.setSingleStep(10.0)
        self.z_spinbox.setDecimals(2)
        slider_layout.addWidget(self.z_spinbox, 2, 1)
        
        self.z_slider = QSlider(Qt.Horizontal)
        self.z_slider.setRange(-2000, 2000)
        self.z_slider.setSingleStep(1)
        self.z_slider.setPageStep(10)
        slider_layout.addWidget(self.z_slider, 2, 2)
        
        # Orientation inputs with sliders
        slider_layout.addWidget(QLabel("Rx:"), 3, 0)
        self.rx_spinbox = QDoubleSpinBox()
        self.rx_spinbox.setRange(-180, 180)
        self.rx_spinbox.setSuffix("°")
        self.rx_spinbox.setSingleStep(5.0)
        self.rx_spinbox.setDecimals(2)
        slider_layout.addWidget(self.rx_spinbox, 3, 1)
        
        self.rx_slider = QSlider(Qt.Horizontal)
        self.rx_slider.setRange(-180, 180)
        self.rx_slider.setSingleStep(1)
        self.rx_slider.setPageStep(5)
        slider_layout.addWidget(self.rx_slider, 3, 2)
        
        slider_layout.addWidget(QLabel("Ry:"), 4, 0)
        self.ry_spinbox = QDoubleSpinBox()
        self.ry_spinbox.setRange(-180, 180)
        self.ry_spinbox.setSuffix("°")
        self.ry_spinbox.setSingleStep(5.0)
        self.ry_spinbox.setDecimals(2)
        slider_layout.addWidget(self.ry_spinbox, 4, 1)
        
        self.ry_slider = QSlider(Qt.Horizontal)
        self.ry_slider.setRange(-180, 180)
        self.ry_slider.setSingleStep(1)
        self.ry_slider.setPageStep(5)
        slider_layout.addWidget(self.ry_slider, 4, 2)
        
        slider_layout.addWidget(QLabel("Rz:"), 5, 0)
        self.rz_spinbox = QDoubleSpinBox()
        self.rz_spinbox.setRange(-180, 180)
        self.rz_spinbox.setSuffix("°")
        self.rz_spinbox.setSingleStep(5.0)
        self.rz_spinbox.setDecimals(2)
        slider_layout.addWidget(self.rz_spinbox, 5, 1)
        
        self.rz_slider = QSlider(Qt.Horizontal)
        self.rz_slider.setRange(-180, 180)
        self.rz_slider.setSingleStep(1)
        self.rz_slider.setPageStep(5)
        slider_layout.addWidget(self.rz_slider, 5, 2)
        
        # Connect sliders and spinboxes
        self.x_spinbox.valueChanged.connect(lambda v: self.x_slider.setValue(int(v)))
        self.x_slider.valueChanged.connect(lambda v: self.x_spinbox.setValue(float(v)))
        
        self.y_spinbox.valueChanged.connect(lambda v: self.y_slider.setValue(int(v)))
        self.y_slider.valueChanged.connect(lambda v: self.y_spinbox.setValue(float(v)))
        
        self.z_spinbox.valueChanged.connect(lambda v: self.z_slider.setValue(int(v)))
        self.z_slider.valueChanged.connect(lambda v: self.z_spinbox.setValue(float(v)))
        
        self.rx_spinbox.valueChanged.connect(lambda v: self.rx_slider.setValue(int(v)))
        self.rx_slider.valueChanged.connect(lambda v: self.rx_spinbox.setValue(float(v)))
        
        self.ry_spinbox.valueChanged.connect(lambda v: self.ry_slider.setValue(int(v)))
        self.ry_slider.valueChanged.connect(lambda v: self.ry_spinbox.setValue(float(v)))
        
        self.rz_spinbox.valueChanged.connect(lambda v: self.rz_slider.setValue(int(v)))
        self.rz_slider.valueChanged.connect(lambda v: self.rz_spinbox.setValue(float(v)))
        
        self.target_layout.addWidget(self.slider_widget)
        
        # Create ESP32 data display widget (will be shown/hidden dynamically)
        self.esp32_data_widget = QWidget()
        esp32_data_layout = QVBoxLayout(self.esp32_data_widget)
        
        # Add three sections with borders and titles
        # 1. Upper arm section
        upper_arm_frame = QGroupBox("Upper Arm Sensor")
        upper_arm_layout = QGridLayout(upper_arm_frame)
        
        # Connection status for upper arm
        upper_arm_layout.addWidget(QLabel("Status:"), 0, 0)
        self.upper_arm_status_label = QLabel("Disconnected")
        self.upper_arm_status_label.setStyleSheet("font-weight: bold; color: gray;")
        upper_arm_layout.addWidget(self.upper_arm_status_label, 0, 1)
        
        # Upper arm sensor values
        upper_arm_layout.addWidget(QLabel("Roll:"), 1, 0)
        self.upper_arm_roll_label = QLabel("0.0°")
        self.upper_arm_roll_label.setStyleSheet("font-weight: bold;")
        upper_arm_layout.addWidget(self.upper_arm_roll_label, 1, 1)
        
        upper_arm_layout.addWidget(QLabel("Pitch:"), 2, 0)
        self.upper_arm_pitch_label = QLabel("0.0°")
        self.upper_arm_pitch_label.setStyleSheet("font-weight: bold;")
        upper_arm_layout.addWidget(self.upper_arm_pitch_label, 2, 1)
        
        # Add to main layout
        esp32_data_layout.addWidget(upper_arm_frame)
        
        # 2. Forearm section
        forearm_frame = QGroupBox("Forearm Sensor")
        forearm_layout = QGridLayout(forearm_frame)
        
        # Connection status for forearm
        forearm_layout.addWidget(QLabel("Status:"), 0, 0)
        self.forearm_status_label = QLabel("Disconnected")
        self.forearm_status_label.setStyleSheet("font-weight: bold; color: gray;")
        forearm_layout.addWidget(self.forearm_status_label, 0, 1)
        
        # Forearm sensor values
        forearm_layout.addWidget(QLabel("Roll:"), 1, 0)
        self.forearm_roll_label = QLabel("0.0°")
        self.forearm_roll_label.setStyleSheet("font-weight: bold;")
        forearm_layout.addWidget(self.forearm_roll_label, 1, 1)
        
        forearm_layout.addWidget(QLabel("Pitch:"), 2, 0)
        self.forearm_pitch_label = QLabel("0.0°")
        self.forearm_pitch_label.setStyleSheet("font-weight: bold;")
        forearm_layout.addWidget(self.forearm_pitch_label, 2, 1)
        
        # Add to main layout
        esp32_data_layout.addWidget(forearm_frame)
        
        # 3. Calculated wrist position
        wrist_frame = QGroupBox("Calculated Wrist Position")
        wrist_layout = QGridLayout(wrist_frame)
        
        # Wrist position values
        wrist_layout.addWidget(QLabel("X:"), 0, 0)
        self.wrist_x_label = QLabel("0.0 mm")
        self.wrist_x_label.setStyleSheet("font-weight: bold;")
        wrist_layout.addWidget(self.wrist_x_label, 0, 1)
        
        wrist_layout.addWidget(QLabel("Y:"), 1, 0)
        self.wrist_y_label = QLabel("0.0 mm")
        self.wrist_y_label.setStyleSheet("font-weight: bold;")
        wrist_layout.addWidget(self.wrist_y_label, 1, 1)
        
        wrist_layout.addWidget(QLabel("Z:"), 2, 0)
        self.wrist_z_label = QLabel("0.0 mm")
        self.wrist_z_label.setStyleSheet("font-weight: bold;")
        wrist_layout.addWidget(self.wrist_z_label, 2, 1)

        
        # Add to main layout
        esp32_data_layout.addWidget(wrist_frame)
        
        # ESP32 data widget is initially hidden - will be shown when ESP32 control mode is selected
        self.esp32_data_widget.hide()
        self.target_layout.addWidget(self.esp32_data_widget)
        
        right_layout.addWidget(target_group)
        
        # Add stretch to push everything up
        right_layout.addStretch(1)
        
        # Add debug log area at the bottom of right panel
        log_group = QGroupBox("Event Log")
        log_layout = QVBoxLayout()
        
        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        self.event_log.setStyleSheet("background-color: #F0F0F0; border: 1px solid #CCC; padding: 5px;")
        self.event_log.setMaximumHeight(150)
        log_layout.addWidget(self.event_log)
        
        # Add clear log button
        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.clicked.connect(self.clear_event_log)
        log_layout.addWidget(clear_log_btn)
        
        # Apply layout to group
        log_group.setLayout(log_layout)
        right_layout.addWidget(log_group)
        
        # Add panels to main layout
        main_layout.addWidget(left_panel, 7)  # 70% width for camera
        main_layout.addWidget(right_panel, 3)  # 30% width for controls
        
        # Create and start camera timer
        self.camera_timer = QTimer(self)
        self.camera_timer.timeout.connect(self.process_camera)
    
    def setup_settings_tab(self):
        """Setup the settings tab with camera and I/O settings"""
        # Main layout as a horizontal layout to split left/right sides
        main_layout = QHBoxLayout(self.settings_tab)
        
        # Left side layout - contains GI/GO Signal Control and I/O Signal Control
        left_layout = QVBoxLayout()
        
        # GI/GO Signal Control group - moved to left side
        gi_go_group = QGroupBox("GI/GO Signal Control")
        gi_go_layout = QVBoxLayout()
        
        # Group signal selection and auto-write on the same row
        gi_go_form = QFormLayout()
        group_signal_layout = QHBoxLayout()
        
        self.group_signal_combo = QComboBox()
        self.group_signal_combo.addItem("Select a group signal")
        group_signal_layout.addWidget(self.group_signal_combo)
        
        # Convert auto-write checkbox to button
        self.auto_write_group_button = QPushButton("Auto Write")
        self.auto_write_group_button.setCheckable(True)
        self.auto_write_group_button.setEnabled(False)
        self.auto_write_group_button.toggled.connect(self.on_auto_write_group_changed)
        group_signal_layout.addWidget(self.auto_write_group_button)
        
        gi_go_form.addRow("Group Signal:", group_signal_layout)
        gi_go_layout.addLayout(gi_go_form)
        
        # Group I/O control buttons
        gi_go_btn_layout = QHBoxLayout()
        self.refresh_group_button = QPushButton("Refresh Group Signals")
        self.refresh_group_button.clicked.connect(self.refresh_group_signals)
        gi_go_btn_layout.addWidget(self.refresh_group_button)
        
        self.write_group_button = QPushButton("Write Gesture to Group")
        self.write_group_button.clicked.connect(self.write_gesture_to_group)
        self.write_group_button.setEnabled(False)
        gi_go_btn_layout.addWidget(self.write_group_button)
        
        gi_go_layout.addLayout(gi_go_btn_layout)
        
        # Remove auto-write checkbox for group signals since we now use a button
        # self.auto_write_group_check = QCheckBox("Auto-write gesture to selected group")
        # self.auto_write_group_check.setEnabled(False)
        # self.auto_write_group_check.stateChanged.connect(self.on_auto_write_group_changed)
        # gi_go_layout.addWidget(self.auto_write_group_check)
        
        # Group signal value table
        self.group_signal_table = QTableWidget(6, 2)
        self.group_signal_table.setHorizontalHeaderLabels(["Fingers", "Group Value"])
        self.group_signal_table.verticalHeader().setVisible(False)
        self.group_signal_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Fill table with default values (0-1 instead of 1-6)
        finger_values = ["0", "1", "2", "3", "4", "5"]
        io_values = ["0", "0", "1", "1", "1", "1"]
        for i in range(6):
            self.group_signal_table.setItem(i, 0, QTableWidgetItem(finger_values[i]))
            self.group_signal_table.setItem(i, 1, QTableWidgetItem(io_values[i]))
        
        gi_go_layout.addWidget(self.group_signal_table)
        
        # Apply layout to group
        gi_go_group.setLayout(gi_go_layout)
        left_layout.addWidget(gi_go_group)
        
        # DO/AO Signal Control group 
        io_group = QGroupBox("I/O Signal Control")
        io_layout = QVBoxLayout()
        
        # I/O signal selection
        io_form = QFormLayout()
        io_signal_layout = QHBoxLayout()
        
        self.io_signal_combo = QComboBox()
        self.io_signal_combo.addItem("Select an I/O signal")
        io_signal_layout.addWidget(self.io_signal_combo)
        
        # Convert auto-write checkbox to button
        self.auto_write_button = QPushButton("Auto Write")
        self.auto_write_button.setCheckable(True)
        self.auto_write_button.setEnabled(False)
        self.auto_write_button.toggled.connect(self.on_auto_write_changed)
        io_signal_layout.addWidget(self.auto_write_button)
        
        io_form.addRow("I/O Signal:", io_signal_layout)
        io_layout.addLayout(io_form)
        
        # I/O control buttons
        io_btn_layout = QHBoxLayout()
        self.refresh_io_button = QPushButton("Refresh I/O Signals")
        self.refresh_io_button.clicked.connect(self.refresh_io_signals)
        io_btn_layout.addWidget(self.refresh_io_button)
        
        self.write_io_button = QPushButton("Write Gesture to I/O")
        self.write_io_button.clicked.connect(self.write_gesture_to_io)
        self.write_io_button.setEnabled(False)
        io_btn_layout.addWidget(self.write_io_button)
        
        io_layout.addLayout(io_btn_layout)
        
        # Remove auto-write checkbox since we now have a button
        # self.auto_write_check = QCheckBox("Auto-write gesture to selected I/O")
        # self.auto_write_check.setEnabled(False)
        # self.auto_write_check.stateChanged.connect(self.on_auto_write_changed)
        # io_layout.addWidget(self.auto_write_check)
        
        # Signal value table - reduce to only 2 rows for finger counts 0 and 5
        self.signal_table = QTableWidget(2, 2)
        self.signal_table.setHorizontalHeaderLabels(["Fingers", "I/O Value"])
        self.signal_table.verticalHeader().setVisible(False)
        self.signal_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Fill table with default values - only 0 and 5 finger counts
        finger_values = ["0", "5"]
        io_values = ["1", "0"]
        for i in range(2):
            self.signal_table.setItem(i, 0, QTableWidgetItem(finger_values[i]))
            self.signal_table.setItem(i, 1, QTableWidgetItem(io_values[i]))
        
        io_layout.addWidget(self.signal_table)
        
        # Add Back Home Position setting
        back_home_layout = QHBoxLayout()
        back_home_layout.addWidget(QLabel("Back Home on Double Tap:"))
        self.back_home_check = QCheckBox()
        self.back_home_check.setChecked(True)
        back_home_layout.addWidget(self.back_home_check)
        
        back_home_layout.addWidget(QLabel("Signal:"))
        # Replace LineEdit with ComboBox for signal selection
        self.back_home_signal = QComboBox()
        self.back_home_signal.addItem("Select a signal")
        back_home_layout.addWidget(self.back_home_signal)
        
        # Add refresh button for home signals
        self.refresh_home_button = QPushButton("Refresh")
        self.refresh_home_button.clicked.connect(self.refresh_home_signals)
        back_home_layout.addWidget(self.refresh_home_button)
        
        # Keep the value spinbox for visual reference, but we'll toggle the actual value
        back_home_layout.addWidget(QLabel("Toggle Value"))
        
        io_layout.addLayout(back_home_layout)
        
        # Add I/O status display
        io_status_group = QGroupBox("I/O Write Status")
        io_status_layout = QFormLayout(io_status_group)
        
        self.io_status_label = QLabel("No signal written")
        self.io_status_label.setStyleSheet("font-weight: bold;")
        io_status_layout.addRow("Last I/O Written:", self.io_status_label)
        
        self.group_status_label = QLabel("No group written")
        self.group_status_label.setStyleSheet("font-weight: bold;")
        io_status_layout.addRow("Last Group Written:", self.group_status_label)
        
        self.home_status_label = QLabel("Not triggered")
        self.home_status_label.setStyleSheet("font-weight: bold;")
        io_status_layout.addRow("Home Position:", self.home_status_label)
        
        io_layout.addWidget(io_status_group)
        
        # Apply layout to group
        io_group.setLayout(io_layout)
        left_layout.addWidget(io_group)
        
        # Add Reset sequence button
        self.reset_sequence_button = QPushButton("Reset EGM Sequence Counter")
        self.reset_sequence_button.setToolTip("Reset sequence counter to fix unresponsive commands")
        self.reset_sequence_button.clicked.connect(self.reset_sequence_counter)
        left_layout.addWidget(self.reset_sequence_button)
        
        # Right side layout - Connection and Camera settings
        right_layout = QVBoxLayout()
        
        # Camera settings group
        camera_settings_group = QGroupBox("Camera Settings")
        camera_settings_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        camera_settings_layout = QVBoxLayout()
        
        # Create two rows with two parameters each, using grid layout
        camera_params_grid = QGridLayout()
        
        # Row 1: Brightness and Contrast
        camera_params_grid.addWidget(QLabel("Brightness:"), 0, 0)
        self.brightness_combo = QComboBox()
        self.brightness_combo.addItems(["Auto", "Low", "Medium", "High"])
        camera_params_grid.addWidget(self.brightness_combo, 0, 1)
        
        camera_params_grid.addWidget(QLabel("Contrast:"), 0, 2)
        self.contrast_combo = QComboBox()
        self.contrast_combo.addItems(["Auto", "Low", "Medium", "High"])
        camera_params_grid.addWidget(self.contrast_combo, 0, 3)
        
        # Row 2: Exposure and Resolution
        camera_params_grid.addWidget(QLabel("Exposure:"), 1, 0)
        self.exposure_combo = QComboBox()
        self.exposure_combo.addItems(["Auto", "1/30", "1/60", "1/125", "1/250", "1/500"])
        camera_params_grid.addWidget(self.exposure_combo, 1, 1)
        
        camera_params_grid.addWidget(QLabel("Resolution:"), 1, 2)
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["640x480", "800x600", "1280x720", "1920x1080"])
        camera_params_grid.addWidget(self.resolution_combo, 1, 3)
        
        # Add grid to main camera settings layout
        camera_settings_layout.addLayout(camera_params_grid)
        
        # Horizontal separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        camera_settings_layout.addWidget(separator)
        
        # Apply settings button
        self.apply_settings_button = QPushButton("Apply Camera Settings")
        self.apply_settings_button.clicked.connect(self.apply_camera_settings)
        self.apply_settings_button.setEnabled(False)
        camera_settings_layout.addWidget(self.apply_settings_button)
        
        # Apply layout to group
        camera_settings_group.setLayout(camera_settings_layout)
        right_layout.addWidget(camera_settings_group)
        
        # Connection settings group (EGM and ESP32)
        connection_settings_group = QGroupBox("Connection Settings")
        connection_settings_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        connection_settings_layout = QVBoxLayout()
        
        # EGM section with title
        egm_label = QLabel("EGM Connection Settings")
        egm_label.setStyleSheet("font-weight: bold; color: #0066CC;")
        connection_settings_layout.addWidget(egm_label)
        
        # EGM port in a grid layout
        egm_layout = QGridLayout()
        egm_layout.addWidget(QLabel("EGM UDP Port:"), 0, 0)
        self.egm_port_spinbox = QSpinBox()
        self.egm_port_spinbox.setRange(1024, 65535)
        self.egm_port_spinbox.setValue(DEFAULT_UDP_PORT)
        egm_layout.addWidget(self.egm_port_spinbox, 0, 1)
        connection_settings_layout.addLayout(egm_layout)
        
        # Separator
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.HLine)
        separator1.setFrameShadow(QFrame.Sunken)
        connection_settings_layout.addWidget(separator1)
        
        # ESP32 section with title
        esp32_label = QLabel("ESP32 Connection Settings")
        esp32_label.setStyleSheet("font-weight: bold; color: #0066CC;")
        connection_settings_layout.addWidget(esp32_label)
        
        # ESP32 port settings - using grid layout for 2 columns
        esp32_port_layout = QGridLayout()
        esp32_port_layout.addWidget(QLabel("Local Port 1:"), 0, 0)
        self.local_port1_spinbox = QSpinBox()
        self.local_port1_spinbox.setRange(1024, 65535)
        self.local_port1_spinbox.setValue(8080)
        esp32_port_layout.addWidget(self.local_port1_spinbox, 0, 1)
        
        esp32_port_layout.addWidget(QLabel("Local Port 2:"), 0, 2)
        self.local_port2_spinbox = QSpinBox()
        self.local_port2_spinbox.setRange(1024, 65535)
        self.local_port2_spinbox.setValue(8081)
        esp32_port_layout.addWidget(self.local_port2_spinbox, 0, 3)
        connection_settings_layout.addLayout(esp32_port_layout)
        
        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setFrameShadow(QFrame.Sunken)
        connection_settings_layout.addWidget(separator2)
        
        # ESP32 calibration offsets section with title
        calibration_label = QLabel("ESP32 Calibration Offsets")
        calibration_label.setStyleSheet("font-weight: bold; color: #0066CC;")
        connection_settings_layout.addWidget(calibration_label)
        
        # Calibration offsets in grid layout (3 columns x 2 rows)
        calibration_layout = QGridLayout()
        
        # X, Y, Z offsets (row 1)
        calibration_layout.addWidget(QLabel("X Offset:"), 0, 0)
        self.x_offset_spinbox = QDoubleSpinBox()
        self.x_offset_spinbox.setRange(-1000, 1000)
        self.x_offset_spinbox.setValue(0.0)
        self.x_offset_spinbox.setSingleStep(1.0)
        self.x_offset_spinbox.setDecimals(2)
        self.x_offset_spinbox.setSuffix(" mm")
        calibration_layout.addWidget(self.x_offset_spinbox, 0, 1)
        
        calibration_layout.addWidget(QLabel("Y Offset:"), 0, 2)
        self.y_offset_spinbox = QDoubleSpinBox()
        self.y_offset_spinbox.setRange(-1000, 1000)
        self.y_offset_spinbox.setValue(0.0)
        self.y_offset_spinbox.setSingleStep(1.0)
        self.y_offset_spinbox.setDecimals(2)
        self.y_offset_spinbox.setSuffix(" mm")
        calibration_layout.addWidget(self.y_offset_spinbox, 0, 3)
        
        calibration_layout.addWidget(QLabel("Z Offset:"), 1, 0)
        self.z_offset_spinbox = QDoubleSpinBox()
        self.z_offset_spinbox.setRange(-1000, 1000)
        self.z_offset_spinbox.setValue(0.0)
        self.z_offset_spinbox.setSingleStep(1.0)
        self.z_offset_spinbox.setDecimals(2)
        self.z_offset_spinbox.setSuffix(" mm")
        calibration_layout.addWidget(self.z_offset_spinbox, 1, 1)
        
        # Rotation offsets (row 2-3)
        calibration_layout.addWidget(QLabel("Rx Offset:"), 2, 0)
        self.rx_offset_spinbox = QDoubleSpinBox()
        self.rx_offset_spinbox.setRange(-180, 180)
        self.rx_offset_spinbox.setValue(0.0)
        self.rx_offset_spinbox.setSingleStep(1.0)
        self.rx_offset_spinbox.setDecimals(2)
        self.rx_offset_spinbox.setSuffix("°")
        calibration_layout.addWidget(self.rx_offset_spinbox, 2, 1)
        
        calibration_layout.addWidget(QLabel("Ry Offset:"), 2, 2)
        self.ry_offset_spinbox = QDoubleSpinBox()
        self.ry_offset_spinbox.setRange(-180, 180)
        self.ry_offset_spinbox.setValue(0.0)
        self.ry_offset_spinbox.setSingleStep(1.0)
        self.ry_offset_spinbox.setDecimals(2)
        self.ry_offset_spinbox.setSuffix("°")
        calibration_layout.addWidget(self.ry_offset_spinbox, 2, 3)
        
        calibration_layout.addWidget(QLabel("Rz Offset:"), 3, 0)
        self.rz_offset_spinbox = QDoubleSpinBox()
        self.rz_offset_spinbox.setRange(-180, 180)
        self.rz_offset_spinbox.setValue(0.0)
        self.rz_offset_spinbox.setSingleStep(1.0)
        self.rz_offset_spinbox.setDecimals(2)
        self.rz_offset_spinbox.setSuffix("°")
        calibration_layout.addWidget(self.rz_offset_spinbox, 3, 1)
        
        connection_settings_layout.addLayout(calibration_layout)
        
        # Separator
        separator3 = QFrame()
        separator3.setFrameShape(QFrame.HLine)
        separator3.setFrameShadow(QFrame.Sunken)
        connection_settings_layout.addWidget(separator3)
        
        # ESP32 scaling factors section with title
        scaling_label = QLabel("ESP32 Scaling Factors")
        scaling_label.setStyleSheet("font-weight: bold; color: #0066CC;")
        connection_settings_layout.addWidget(scaling_label)
        
        # Scaling factors in grid layout
        scaling_layout = QGridLayout()
        
        # X, Y, Z scaling factors (row 1-2)
        scaling_layout.addWidget(QLabel("X Scale:"), 0, 0)
        self.x_scale_spinbox = QDoubleSpinBox()
        self.x_scale_spinbox.setRange(0.1, 10.0)
        self.x_scale_spinbox.setValue(1.0)
        self.x_scale_spinbox.setSingleStep(0.1)
        self.x_scale_spinbox.setDecimals(2)
        scaling_layout.addWidget(self.x_scale_spinbox, 0, 1)
        
        scaling_layout.addWidget(QLabel("Y Scale:"), 0, 2)
        self.y_scale_spinbox = QDoubleSpinBox()
        self.y_scale_spinbox.setRange(0.1, 10.0)
        self.y_scale_spinbox.setValue(1.0)
        self.y_scale_spinbox.setSingleStep(0.1)
        self.y_scale_spinbox.setDecimals(2)
        scaling_layout.addWidget(self.y_scale_spinbox, 0, 3)
        
        scaling_layout.addWidget(QLabel("Z Scale:"), 1, 0)
        self.z_scale_spinbox = QDoubleSpinBox()
        self.z_scale_spinbox.setRange(0.1, 10.0)
        self.z_scale_spinbox.setValue(1.0)
        self.z_scale_spinbox.setSingleStep(0.1)
        self.z_scale_spinbox.setDecimals(2)
        scaling_layout.addWidget(self.z_scale_spinbox, 1, 1)
        
        # Rotation scaling (row 2)
        scaling_layout.addWidget(QLabel("Rotation Scale:"), 1, 2)
        self.rot_scale_spinbox = QDoubleSpinBox()
        self.rot_scale_spinbox.setRange(0.01, 1.0)
        self.rot_scale_spinbox.setValue(0.1)
        self.rot_scale_spinbox.setSingleStep(0.01)
        self.rot_scale_spinbox.setDecimals(2)
        scaling_layout.addWidget(self.rot_scale_spinbox, 1, 3)
        
        connection_settings_layout.addLayout(scaling_layout)
        
        # Separator
        separator4 = QFrame()
        separator4.setFrameShape(QFrame.HLine)
        separator4.setFrameShadow(QFrame.Sunken)
        connection_settings_layout.addWidget(separator4)
        
        # Apply ESP32 settings button
        self.apply_esp32_settings_button = QPushButton("Apply ESP32 Settings")
        self.apply_esp32_settings_button.clicked.connect(self.apply_esp32_settings)
        self.apply_esp32_settings_button.setEnabled(True)
        connection_settings_layout.addWidget(self.apply_esp32_settings_button)
        
        # Apply layout to group
        connection_settings_group.setLayout(connection_settings_layout)
        right_layout.addWidget(connection_settings_group)
        
        # Add left and right layouts to main layout
        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 1)
        
        # Log initialization
        self.log_event("Settings tab setup complete")
    
    def update_cartesian_position(self, cartesian_data):
        """Update cartesian position labels with latest values"""
        self.x_label.setText(f"{cartesian_data['x']:.2f} mm")
        self.y_label.setText(f"{cartesian_data['y']:.2f} mm")
        self.z_label.setText(f"{cartesian_data['z']:.2f} mm")
        self.rx_label.setText(f"{cartesian_data['rx']:.2f}°")
        self.ry_label.setText(f"{cartesian_data['ry']:.2f}°")
        self.rz_label.setText(f"{cartesian_data['rz']:.2f}°")
        
        # Initialize sliders with current position (only once)
        if not self.slider_initialized:
            # Set sliders to current position
            self.x_spinbox.setValue(cartesian_data['x'])
            self.y_spinbox.setValue(cartesian_data['y'])
            self.z_spinbox.setValue(cartesian_data['z'])
            self.rx_spinbox.setValue(cartesian_data['rx'])
            self.ry_spinbox.setValue(cartesian_data['ry'])
            self.rz_spinbox.setValue(cartesian_data['rz'])
            
            # Set sliders
            self.x_slider.setValue(int(cartesian_data['x']))
            self.y_slider.setValue(int(cartesian_data['y']))
            self.z_slider.setValue(int(cartesian_data['z']))
            self.rx_slider.setValue(int(cartesian_data['rx']))
            self.ry_slider.setValue(int(cartesian_data['ry']))
            self.rz_slider.setValue(int(cartesian_data['rz']))
            
            # Mark as initialized
            self.slider_initialized = True
            self.log_event("Control sliders initialized with current position")
            self.update_debug_log("Control sliders initialized with current position")
    
    def update_esp32_position(self, esp32_data):
        """Update ESP32 position data and forward to EGM worker"""
        self.egm_worker.set_esp32_position(esp32_data)
        
        # Update ESP32 sensor displays if in ESP32 control mode
        if self.control_mode_combo.currentText() == "ESP32 Wrist Control":
            # Update connection status for each sensor
            if esp32_data.get('device_id') == 1:
                self.upper_arm_status_label.setText("Connected")
                self.upper_arm_status_label.setStyleSheet("font-weight: bold; color: green;")
                # Update upper arm sensor values
                self.upper_arm_roll_label.setText(f"{esp32_data['rx']:.2f}°")
                self.upper_arm_pitch_label.setText(f"{esp32_data['ry']:.2f}°")
            elif esp32_data.get('device_id') == 2:
                self.forearm_status_label.setText("Connected")
                self.forearm_status_label.setStyleSheet("font-weight: bold; color: green;")
                # Update forearm sensor values
                self.forearm_roll_label.setText(f"{esp32_data['rz']:.2f}°")
                self.forearm_pitch_label.setText(f"{esp32_data['rx'] + esp32_data['ry']:.2f}°")
            
            # Update calculated wrist position display
            self.wrist_x_label.setText(f"{esp32_data['x']:.2f} mm")
            self.wrist_y_label.setText(f"{esp32_data['y']:.2f} mm")
            self.wrist_z_label.setText(f"{esp32_data['z']:.2f} mm")
    
    def update_status(self, status):
        """Update status label"""
        self.status_label.setText(status)
        self.log_event(status)
    
    def handle_error(self, error_msg):
        """Handle error from worker thread"""
        self.log_event(f"Error: {error_msg}")
        QMessageBox.critical(self, "Error", error_msg)
    
    def update_connection_status(self, connected):
        """Update UI based on connection status"""
        if connected:
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("font-weight: bold; color: green;")
        else:
            self.status_label.setText("Not connected")
            self.status_label.setStyleSheet("font-weight: bold; color: red;")
            
            # If disconnected unexpectedly, enable start button
            if not self.start_button.isEnabled() and self.stop_button.isEnabled():
                self.start_button.setEnabled(True)
                self.stop_button.setEnabled(False)
                self.egm_port_spinbox.setEnabled(True)
    
    def update_debug_log(self, message):
        """Add message to debug log (now going to event log)"""
        # Forward to log_event for unified logging
        self.log_event(message)
    
    def log_event(self, message):
        """Add message to event log"""
        import time
        import traceback
        
        try:
            # Get timestamp
            timestamp = time.strftime("%H:%M:%S")
            
            # Append to event log
            if hasattr(self, 'event_log'):
                self.event_log.append(f"[{timestamp}] {message}")
                # Auto-scroll to bottom
                cursor = self.event_log.textCursor()
                cursor.movePosition(cursor.End)
                self.event_log.setTextCursor(cursor)
                
            # Also print to console for debugging
            print(f"[{timestamp}] {message}")
        except Exception as e:
            print(f"Error in log_event: {str(e)}\n{traceback.format_exc()}")
    
    def clear_event_log(self):
        """Clear the event log"""
        if hasattr(self, 'event_log'):
            self.event_log.clear()
            self.log_event("Event log cleared")
    
    def get_slider_values(self):
        """Get current values from sliders/spinboxes for EGM worker"""
        if not hasattr(self, 'x_spinbox'):
            return None
            
        # Return current values from spinboxes
        return {
            "x": self.x_spinbox.value(),
            "y": self.y_spinbox.value(),
            "z": self.z_spinbox.value(),
            "rx": self.rx_spinbox.value(),
            "ry": self.ry_spinbox.value(),
            "rz": self.rz_spinbox.value()
        }
    
    def start_egm(self):
        """Start EGM communication"""
        try:
            # Configure EGM worker
            port = self.egm_port_spinbox.value()
            self.egm_worker.configure(port)
            
            # Start worker thread
            self.egm_worker.start()
            
            # Update UI
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            
            self.log_event(f"Started EGM on port {port}")
            
        except Exception as e:
            error_msg = f"Failed to start EGM: {str(e)}"
            self.log_event(f"Error: {error_msg}")
            QMessageBox.critical(self, "EGM Error", error_msg)
    
    def stop_egm(self):
        """Stop EGM communication"""
        try:
            # Stop worker thread
            self.update_debug_log("Stopping EGM worker thread")
            self.egm_worker.stop()
            
            # Update UI
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.egm_port_spinbox.setEnabled(True)
            
            self.log_event("Stopped EGM")
            
        except Exception as e:
            error_msg = f"Failed to stop EGM: {str(e)}"
            self.log_event(f"Error: {error_msg}")
            self.update_debug_log(f"Error stopping EGM: {str(e)}\n{traceback.format_exc()}")
            QMessageBox.critical(self, "EGM Error", error_msg)
    
    def connect_esp32(self):
        """Connect to ESP32 wrist controller"""
        try:
            # Get connection parameters from settings tab
            local_port1 = self.local_port1_spinbox.value()
            local_port2 = self.local_port2_spinbox.value()
            
            # Configure ESP32 worker with both local ports
            self.esp32_worker.configure_dual_ports(None, local_port1, local_port2)
            
            # Start worker thread
            self.esp32_worker.start()
            
            # Update UI
            self.connect_esp32_button.setEnabled(False)
            self.disconnect_esp32_button.setEnabled(True)
            self.apply_esp32_settings_button.setEnabled(True)
            
            self.log_event(f"ESP32 socket server started on ports {local_port1} and {local_port2}")
            self.esp32_status_label.setText("Connected")
            self.esp32_status_label.setStyleSheet("font-weight: bold; color: green;")
            
        except Exception as e:
            error_msg = f"Failed to connect to ESP32: {str(e)}"
            self.log_event(f"Error: {error_msg}")
            QMessageBox.critical(self, "ESP32 Error", error_msg)
    
    def disconnect_esp32(self):
        """Disconnect from ESP32 wrist controller"""
        try:
            # Stop worker thread
            self.esp32_worker.stop()
            
            # Update UI
            self.connect_esp32_button.setEnabled(True)
            self.disconnect_esp32_button.setEnabled(False)
            self.apply_esp32_settings_button.setEnabled(True)
            
            self.log_event("Disconnected from ESP32")
            self.esp32_status_label.setText("Not connected")
            self.esp32_status_label.setStyleSheet("font-weight: bold; color: red;")
            
            # If control mode was ESP32, switch back to sliders
            if self.control_mode_combo.currentText() == "ESP32 Wrist Control":
                self.control_mode_combo.setCurrentIndex(0)  # Switch to sliders
            
        except Exception as e:
            error_msg = f"Failed to disconnect from ESP32: {str(e)}"
            self.log_event(f"Error: {error_msg}")
            QMessageBox.critical(self, "ESP32 Error", error_msg)
    
    def calibrate_esp32(self):
        """Calibrate ESP32 wrist controller with current robot position"""
        try:
            # Get current robot position from EGM worker
            if self.egm_worker.last_position:
                # Calibrate ESP32 with current robot position
                self.esp32_worker.calibrate(self.egm_worker.last_position)
                self.log_event("ESP32 calibrated with current robot position")
            else:
                self.log_event("Cannot calibrate ESP32 - no robot position available")
        except Exception as e:
            error_msg = f"Failed to calibrate ESP32: {str(e)}"
            self.log_event(f"Error: {error_msg}")
            self.update_debug_log(f"Error calibrating ESP32: {str(e)}\n{traceback.format_exc()}")
            QMessageBox.critical(self, "ESP32 Error", error_msg)
    
    def apply_esp32_settings(self):
        """Apply ESP32 settings"""
        try:
            # Get scaling factors from UI
            scaling_factors = {
                "x_scale": self.x_scale_spinbox.value(),
                "y_scale": self.y_scale_spinbox.value(),
                "z_scale": self.z_scale_spinbox.value(),
                "rx_scale": self.rot_scale_spinbox.value(),
                "ry_scale": self.rot_scale_spinbox.value(),
                "rz_scale": self.rot_scale_spinbox.value()
            }
            
            # Get calibration offsets from UI
            calibration_offsets = {
                "x_offset": self.x_offset_spinbox.value(),
                "y_offset": self.y_offset_spinbox.value(),
                "z_offset": self.z_offset_spinbox.value(),
                "rx_offset": self.rx_offset_spinbox.value(),
                "ry_offset": self.ry_offset_spinbox.value(),
                "rz_offset": self.rz_offset_spinbox.value()
            }
            
            # Apply scaling factors to ESP32 worker
            self.esp32_worker.set_scaling(scaling_factors)
            
            # Apply calibration offsets to ESP32 worker
            self.esp32_worker.set_calibration(calibration_offsets)
            
            self.log_event("Applied ESP32 settings")
            
        except Exception as e:
            error_msg = f"Failed to apply ESP32 settings: {str(e)}"
            self.log_event(f"Error: {error_msg}")
            self.update_debug_log(f"Error applying ESP32 settings: {str(e)}\n{traceback.format_exc()}")
            QMessageBox.critical(self, "ESP32 Error", error_msg)
    
    def connect_camera(self):
        """Connect to the selected camera"""
        camera_idx = self.camera_combo.currentIndex()
        self.log_event(f"Connecting to camera: {camera_idx}")
        
        try:
            # Close current camera if open
            if self.camera is not None:
                self.stop_stream()
                self.camera.release()
                self.camera = None
            
            # Open new camera
            self.camera = cv2.VideoCapture(camera_idx)
            
            if not self.camera.isOpened():
                self.log_event(f"Failed to open camera {camera_idx}")
                return
                
            # Read a frame to verify connection
            ret, frame = self.camera.read()
            if not ret or frame is None:
                self.log_event("Failed to capture frame from camera")
                self.camera.release()
                self.camera = None
                return
            
            # Update UI
            self.start_stream_button.setEnabled(True)
            self.connect_camera_button.setEnabled(False)
            self.disconnect_camera_button.setEnabled(True)
            self.apply_settings_button.setEnabled(True)
            
            self.log_event(f"Connected to camera {camera_idx} successfully")
            
        except Exception as e:
            error_msg = f"Failed to connect to camera: {str(e)}"
            self.log_event(f"Error: {error_msg}")
            self.update_debug_log(f"Error connecting to camera: {str(e)}\n{traceback.format_exc()}")
            if self.camera:
                self.camera.release()
                self.camera = None
    
    def start_stream(self):
        """Start the video stream"""
        if not self.camera:
            self.log_event("Cannot start stream - no camera connected")
            return
            
        try:
            # Get current resolution
            width, height = [int(x) for x in self.resolution_combo.currentText().split('x')]
            
            # Set resolution
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            
            # Start streaming
            self.is_streaming = True
            
            # Start camera timer
            self.camera_timer.start(30)  # 30ms = ~33 fps
            
            # Update UI
            self.stop_stream_button.setEnabled(True)
            self.start_stream_button.setEnabled(False)
            
            self.log_event("Video stream started")
            
        except Exception as e:
            error_msg = f"Failed to start video stream: {str(e)}"
            self.log_event(f"Error: {error_msg}")
            self.update_debug_log(f"Error starting video stream: {str(e)}\n{traceback.format_exc()}")
            self.is_streaming = False
    
    def stop_stream(self):
        """Stop the video stream"""
        if not self.is_streaming:
            return
            
        try:
            # Stop streaming
            self.is_streaming = False
            
            # Stop camera timer
            if self.camera_timer.isActive():
                self.camera_timer.stop()
            
            # Clear video label
            self.video_label.setText("No video feed")
            self.processed_frame = None
            
            # Update UI
            self.stop_stream_button.setEnabled(False)
            self.start_stream_button.setEnabled(True)
            
            self.log_event("Video stream stopped")
            
        except Exception as e:
            error_msg = f"Failed to stop video stream: {str(e)}"
            self.log_event(f"Error: {error_msg}")
            self.update_debug_log(f"Error stopping video stream: {str(e)}\n{traceback.format_exc()}")
    
    def process_camera(self):
        """Process camera frame and detect hand gestures"""
        if not self.camera or not self.is_streaming:
            return
            
        try:
            # Read frame from camera
            ret, frame = self.camera.read()
            if not ret or frame is None:
                self.log_event("Error reading frame from camera")
                return
                
            # Flip image horizontally for easier use
            frame = cv2.flip(frame, 1)
            
            # Process frame with hand detector if available
            if self.hand_detector and self.mediapipe_available:
                processed_frame, hand_lms = self.hand_detector.findHands(frame)
                
                # Count fingers
                n_fingers = self.hand_detector.count_finger(hand_lms)
                
                # Get hand gesture
                hand_gesture = self.hand_detector.get_hand_gesture(n_fingers)
                Trigger = 0
                # Get option
                hand_option = self.hand_detector.get_option(n_fingers)
                
                # --- Double tap detection ---
                fingers_touching, tap_count, status = self.hand_detector.update_double_tap(hand_lms, 4, 8)
                
                # Update tap label
                self.tap_label.setText(str(tap_count))
                
                double_tap_active = False
                if status == "triggered" or status == "reset":
                    hand_gesture += " + Đã kích hoạt!"
                    self.log_event("Double tap: Đã kích hoạt!")
                    double_tap_active = True
                    
                    # Update double tap status display
                    self.double_tap_status.setText("ACTIVE")
                    self.double_tap_status.setStyleSheet("font-weight: bold; color: green;")
                    
                    # Handle back home position if enabled
                    if self.back_home_check.isChecked() and self.back_home_signal.currentText() != "Select a signal":
                        signal_name = self.back_home_signal.currentText()
                        
                        # First get the current signal value properly
                        try:
                            # Get the proper signal path
                            signal_path = f"/rw/iosystem/signals/{signal_name}"
                            
                            # Get current value directly from robot controller
                            result = self.robot.io.get_signal_value(signal_path)
                            
                            if result.get('status_code') == 200 and 'content' in result:
                                # Extract the current value from the response
                                current_value = None

                                # Extract value in different possible formats
                                if 'value' in result['content']:
                                    current_value = result['content']['value']
                                elif 'state' in result['content'] and len(result['content']['state']) > 0:
                                    for state in result['content']['state']:
                                        if 'lvalue' in state:
                                            current_value = state['lvalue']
                                            break
                                elif '_embedded' in result['content'] and 'resources' in result['content']['_embedded']:
                                    resources = result['content']['_embedded']['resources']
                                    if len(resources) > 0 and 'lvalue' in resources[0]:
                                        current_value = resources[0]['lvalue']
                                # ...existing code...
                                
                                if current_value is not None:
                                    # Convert to integer
                                    try:
                                        current_value = int(current_value)
                                    except (ValueError, TypeError):
                                        current_value = 0
                                        
                                    self.log_event(f"Current value of {signal_name}: {current_value}")
                                    
                                    # Toggle value (0->1, 1->0)
                                    new_value = 0 if current_value == 1 else 1
                                    self.log_event(f"Toggling {signal_name} from {current_value} to {new_value}")
                                    
                                    # Write toggled value
                                    success = self.write_signal_value(signal_name, new_value)
                                    
                                    if success:
                                        self.home_status_label.setText(f"{signal_name} = {new_value} (toggled from {current_value})")
                                        self.home_status_label.setStyleSheet("font-weight: bold; color: green;")
                                        self.log_event(f"Back home triggered: {signal_name} toggled from {current_value} to {new_value}")
                                else:
                                    self.log_event(f"Could not extract current value from response: {result}")
                                    self.home_status_label.setText(f"Error: Could not extract value")
                                    self.home_status_label.setStyleSheet("font-weight: bold; color: red;")
                            else:
                                error_msg = f"Failed to get current signal value: {result.get('error', 'Unknown error')}"
                                self.log_event(error_msg)
                                self.home_status_label.setText(error_msg)
                                self.home_status_label.setStyleSheet("font-weight: bold; color: red;")
                        except Exception as e:
                            self.log_event(f"Error toggling home signal: {str(e)}")
                            self.home_status_label.setText(f"Error: {str(e)}")
                            self.home_status_label.setStyleSheet("font-weight: bold; color: red;")
                
                else:
                    # Update double tap status display for idle state
                    self.double_tap_status.setText("Not Active")
                    self.double_tap_status.setStyleSheet("font-weight: bold; color: gray;")

                # --- End double tap ---
                
                # Display option information on image
                if hand_option > 0:
                    cv2.putText(processed_frame, f"Option: {hand_option}", 
                               (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                # Hiển thị trạng thái double tap lên ảnh
                cv2.putText(processed_frame, f"Tap Count: {tap_count}", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
                
                # Add double tap status to image
                double_tap_text = "Double Tap: ACTIVE" if double_tap_active else "Double Tap: Inactive"
                double_tap_color = (0, 255, 0) if double_tap_active else (0, 0, 255)
                cv2.putText(processed_frame, double_tap_text, (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, double_tap_color, 2)
                
                # Save results
                self.processed_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)  # Convert to RGB for Qt
                self.n_fingers = n_fingers
                self.last_detected_gesture = hand_gesture
                self.hand_option = hand_gesture
                
                # Update UI with gesture info
                self.fingers_label.setText(str(self.n_fingers))
                self.gesture_label.setText(self.last_detected_gesture)
                
                # Process I/O auto-write if enabled and robot connected
                if self.robot:
                    # Only process if hand is detected
                    if n_fingers >= 0 and hand_gesture != "Không phát hiện tay":
                        # Regular I/O
                        if self.auto_write_button.isChecked():
                            self.write_gesture_to_io()
                        
                        # Group I/O
                        if hasattr(self, 'auto_write_group_button') and self.auto_write_group_button.isChecked():
                            self.write_gesture_to_group()
                
            else:
                # If hand detector not available, just show original image with a notice
                h, w, _ = frame.shape
                cv2.putText(frame, "MediaPipe not available", (int(w/4), int(h/2)-30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                self.processed_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.n_fingers = -1
                self.last_detected_gesture = "MediaPipe không khả dụng"
                self.hand_option = -1
                
            # Update video label with processed frame
            self.update_video_label()
                
        except Exception as e:
            self.log_event(f"Error processing camera: {str(e)}")
            self.update_debug_log(f"Error processing camera: {str(e)}\n{traceback.format_exc()}")
    
    def update_video_label(self):
        """Update video label with latest processed frame"""
        if self.processed_frame is not None:
            try:
                # Convert frame from OpenCV to QImage for display
                h, w, ch = self.processed_frame.shape
                bytes_per_line = ch * w
                qt_image = QImage(self.processed_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_image)
                
                # Scale pixmap to fit label while maintaining aspect ratio
                pixmap = pixmap.scaled(self.video_label.width(), self.video_label.height(), 
                                      Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
                # Set pixmap to label
                self.video_label.setPixmap(pixmap)
            except Exception as e:
                self.update_debug_log(f"Error updating video label: {str(e)}")
    
    def apply_camera_settings(self):
        """Apply camera settings"""
        if not self.camera:
            self.log_event("Cannot apply settings - no camera connected")
            return
            
        try:
            # Create settings dictionary
            settings = {}
            
            # Brightness
            brightness_map = {"Low": 0, "Medium": 50, "High": 100, "Auto": -1}
            settings['brightness'] = brightness_map[self.brightness_combo.currentText()]
            
            # Contrast
            contrast_map = {"Low": 0, "Medium": 50, "High": 100, "Auto": -1}
            settings['contrast'] = contrast_map[self.contrast_combo.currentText()]
            
            # Resolution
            width, height = [int(x) for x in self.resolution_combo.currentText().split('x')]
            settings['width'] = width
            settings['height'] = height
            
            # Exposure
            exposure_map = {"1/30": -5, "1/60": -6, "1/125": -7, "1/250": -8, "1/500": -9, "Auto": 0}
            settings['exposure'] = exposure_map[self.exposure_combo.currentText()]
            
            # Apply settings
            self.camera.set(cv2.CAP_PROP_BRIGHTNESS, settings['brightness'] if settings['brightness'] >= 0 else 0.5)
            self.camera.set(cv2.CAP_PROP_CONTRAST, settings['contrast'] if settings['contrast'] >= 0 else 0.5)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, settings['width'])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, settings['height'])
            
            # Handle exposure separately due to auto vs manual modes
            if settings['exposure'] == 0:  # Auto
                self.camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3)  # 3 = auto
            else:
                self.camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # 1 = manual
                self.camera.set(cv2.CAP_PROP_EXPOSURE, settings['exposure'])
            
            self.log_event("Camera settings applied")
            
        except Exception as e:
            error_msg = f"Failed to apply camera settings: {str(e)}"
            self.log_event(f"Error: {error_msg}")
            self.update_debug_log(f"Error applying camera settings: {str(e)}\n{traceback.format_exc()}")
    
    def change_control_mode(self, index):
        """Change the robot control mode"""
        mode_text = self.control_mode_combo.currentText()
        
        if mode_text == "UI Sliders":
            self.egm_worker.set_control_mode("SLIDERS")
            self.log_event("Control mode changed to UI Sliders")
            
            # Switch to slider widget in target position control
            if hasattr(self, 'esp32_data_widget'):
                self.esp32_data_widget.hide()
                self.slider_widget.show()
            
        elif mode_text == "ESP32 Wrist Control":
            # Check if ESP32 is connected
            if not self.esp32_worker.running:
                QMessageBox.warning(self, "ESP32 Not Connected", 
                                   "Please connect to ESP32 first")
                # Switch back to sliders without triggering another event
                self.control_mode_combo.blockSignals(True)
                self.control_mode_combo.setCurrentIndex(0)
                self.control_mode_combo.blockSignals(False)
                return
                
            self.egm_worker.set_control_mode("ESP32")
            self.log_event("Control mode changed to ESP32 Wrist Control")
            
            # Switch to ESP32 data widget in target position control
            if hasattr(self, 'slider_widget'):
                self.slider_widget.hide()
                self.esp32_data_widget.show()
    
    def refresh_io_signals(self):
        """Refresh I/O signals from robot controller"""
        if not self.robot:
            self.log_event("Cannot refresh I/O signals - no robot connection")
            return
            
        try:
            # Clear current list
            self.io_signal_combo.clear()
            self.io_signal_combo.addItem("Select an I/O signal")
            
            # Get I/O signals from robot
            signals = self.robot.io.search_signals()
            
            if signals.get('status_code') == 200 and 'content' in signals:
                if '_embedded' in signals['content'] and 'resources' in signals['content']['_embedded']:
                    signal_list = signals['content']['_embedded']['resources']
                    
                    # Filter digital output signals
                    for signal in signal_list:
                        signal_name = signal.get('name', '')
                        signal_type = signal.get('type', '')
                        
                        if signal_type == 'DI' or signal_type == 'DO':  # Digital Output or Group Output
                            self.io_signal_combo.addItem(signal_name)
                    
                    self.log_event(f"Loaded {self.io_signal_combo.count()-1} digital output signals")
                    
                    # Enable controls if signals are available
                    if self.io_signal_combo.count() > 1:
                        self.write_io_button.setEnabled(True)
                        self.auto_write_button.setEnabled(True)
            
        except Exception as e:
            error_msg = f"Failed to refresh I/O signals: {str(e)}"
            self.log_event(f"Error: {error_msg}")
            self.update_debug_log(f"Error refreshing I/O signals: {str(e)}\n{traceback.format_exc()}")
    
    def refresh_home_signals(self):
        """Refresh signals for home position selection"""
        if not self.robot:
            self.log_event("Cannot refresh home signals - no robot connection")
            return
            
        try:
            # Clear current list
            self.back_home_signal.clear()
            self.back_home_signal.addItem("Select a signal")
            
            # Get I/O signals from robot
            signals = self.robot.io.search_signals()
            
            if signals.get('status_code') == 200 and 'content' in signals:
                if '_embedded' in signals['content'] and 'resources' in signals['content']['_embedded']:
                    signal_list = signals['content']['_embedded']['resources']
                    
                    # Add all signal types
                    for signal in signal_list:
                        signal_name = signal.get('name', '')
                        signal_type = signal.get('type', '')
                        
                        # Include all digital signals
                        if signal_type in ['DI', 'DO', 'GI', 'GO']:
                            self.back_home_signal.addItem(signal_name)
                    
                    self.log_event(f"Loaded {self.back_home_signal.count()-1} signals for home position")
            
        except Exception as e:
            error_msg = f"Failed to refresh home signals: {str(e)}"
            self.log_event(f"Error: {error_msg}")
            self.update_debug_log(f"Error refreshing home signals: {str(e)}\n{traceback.format_exc()}")
    
    def write_gesture_to_io(self):
        """Write current gesture value to selected I/O signal"""
        if not self.robot:
            self.log_event("Cannot write to I/O - no robot connection")
            return
            
        signal_name = self.io_signal_combo.currentText()
        if signal_name == "Select an I/O signal":
            # Only show message if manual button press (not auto-write)
            if not self.auto_write_button.isChecked():
                self.log_event("Please select an I/O signal first")
            return
            
        try:
            # Check if hand is detected - skip if no hand detected
            if self.n_fingers < 0 or self.last_detected_gesture == "Không phát hiện tay":
                return
                
            # Get available finger values from the table
            available_finger_values = []
            for i in range(self.signal_table.rowCount()):
                finger_value_str = self.signal_table.item(i, 0).text()
                try:
                    finger_value = int(finger_value_str)
                    available_finger_values.append((i, finger_value))
                except ValueError:
                    self.log_event(f"Invalid finger value in table: {finger_value_str}")
            
            # Consider special cases like closed fist or open hand
            is_fist = "nắm đấm" in self.last_detected_gesture.lower() or "fist" in self.last_detected_gesture.lower()
            is_open_hand = "open" in self.last_detected_gesture.lower() or "mở" in self.last_detected_gesture.lower()
            
            # Adjust finger count based on gesture detection
            effective_finger_count = self.n_fingers
            if is_fist and effective_finger_count != 0:
                # Force to 0 for fist gesture
                effective_finger_count = 0
                self.log_event(f"Detected fist gesture, treating as {effective_finger_count} fingers")
            elif is_open_hand and effective_finger_count != 5:
                # Force to 5 for open hand gesture
                effective_finger_count = 5
                self.log_event(f"Detected open hand gesture, treating as {effective_finger_count} fingers")
            
            # Find matching finger value in table
            table_index = -1
            for idx, value in available_finger_values:
                if value == effective_finger_count:
                    table_index = idx
                    break
            
            # Process if we found a matching finger value
            if table_index >= 0:
                # Log the detected gesture and matched finger value
                finger_value = self.signal_table.item(table_index, 0).text()
                self.log_event(f"Processing gesture: {self.last_detected_gesture}, matched with table value: {finger_value}")
                
                # Get corresponding I/O value from table
                io_value = int(self.signal_table.item(table_index, 1).text())
                
                # Write value to robot I/O using our utility method
                success = self.write_signal_value(signal_name, io_value)
                
                # Update status display
                if success:
                    self.io_status_label.setText(f"{signal_name} = {io_value}")
                    self.io_status_label.setStyleSheet("font-weight: bold; color: green;")
            else:
                # Log that we didn't find a matching finger value in the table
                available_values = [str(value) for _, value in available_finger_values]
                self.log_event(f"Finger count {effective_finger_count} not found in table (available values: {', '.join(available_values)}), maintaining previous value")
                
        except Exception as e:
            import traceback
            self.log_event(f"Error writing to I/O signal: {str(e)}")
            self.update_debug_log(f"Error details: \n{traceback.format_exc()}")
            
            # Update status display for error
            self.io_status_label.setText(f"Error: {str(e)}")
            self.io_status_label.setStyleSheet("font-weight: bold; color: red;")
    
    def on_auto_write_changed(self, state):
        """Handle auto-write checkbox state change"""
        if state == Qt.Checked:
            signal_name = self.io_signal_combo.currentText()
            if signal_name == "Select an I/O signal":
                self.log_event("Please select an I/O signal first")
                self.auto_write_button.setChecked(False)
            else:
                self.log_event(f"Auto-write enabled for signal {signal_name}")
                # Update button style for active state
                self.auto_write_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        else:
            self.log_event("Auto-write disabled")
            # Reset button style
            self.auto_write_button.setStyleSheet("")
    
    def force_release_port(self):
        """Force release of UDP port"""
        try:
            port = self.egm_port_spinbox.value()
            self.log_event(f"Attempting to force release port {port}")
            
            # Code to release port
            # ...
            
            self.log_event(f"Port {port} released successfully")
            
        except Exception as e:
            error_msg = f"Failed to release port: {str(e)}"
            self.log_event(f"Error: {error_msg}")
            QMessageBox.critical(self, "Port Error", error_msg)
            
    def reset_sequence_counter(self):
        """Reset the sequence counter to ensure fresh commands"""
        if not self.egm_worker.running or not self.egm_worker.egm_client:
            QMessageBox.warning(self, "EGM Not Running", "EGM must be started first")
            return
            
        try:
            # Use worker's method to reset the sequence counter
            self.update_debug_log("Resetting sequence counter")
            success = self.egm_worker.reset_sequence_counter()
            
            if success:
                self.log_event("Sequence counter reset")
                
                # Force a packet to be sent to update the robot controller
                self.update_debug_log("Sending test packet with new sequence number")
                try:
                    # Get current position
                    current_pos = self.get_slider_values()
                    if current_pos:
                        # Send the current position back to ensure a smooth reset
                        self.egm_worker.send_cartesian_target(**current_pos)
                        self.log_event("Test packet sent with new sequence number")
                    else:
                        self.update_debug_log("Could not get current position, sending default position")
                        # Send a default position close to home
                        self.egm_worker.send_cartesian_target(600, 0, 800, 0, 0, 0)
                except Exception as e:
                    self.update_debug_log(f"Error sending test packet: {str(e)}")
            else:
                self.log_event("Failed to reset sequence counter")
            
        except Exception as e:
            self.update_debug_log(f"Error resetting sequence counter: {str(e)}\n{traceback.format_exc()}")
            QMessageBox.critical(self, "Error", f"Failed to reset sequence counter: {str(e)}")
    
    def update_ui(self):
        """Update UI elements - called periodically by timer"""
        # Update connection status for EGM
        if self.egm_worker.running and hasattr(self.egm_worker, 'egm_client') and self.egm_worker.egm_client:
            # Update connection state
            self.robot_state_label.setText("CONNECTED")
            self.robot_state_label.setStyleSheet("font-weight: bold; color: green;")
            
            # Update sliders with current position if they don't have focus and in SLIDERS mode
            if self.egm_worker.control_mode == "SLIDERS":
                spinboxes = {
                    'x': self.x_spinbox, 'y': self.y_spinbox, 'z': self.z_spinbox,
                    'rx': self.rx_spinbox, 'ry': self.ry_spinbox, 'rz': self.rz_spinbox
                }
                sliders = {
                    'x': self.x_slider, 'y': self.y_slider, 'z': self.z_slider,
                    'rx': self.rx_slider, 'ry': self.ry_slider, 'rz': self.rz_slider
                }
                self.egm_worker.update_sliders_with_position(spinboxes, sliders)
        else:
            # Not connected
            self.robot_state_label.setText("DISCONNECTED")
            self.robot_state_label.setStyleSheet("font-weight: bold; color: gray;")
        
        # Update ESP32 connection status
        if self.esp32_worker.running:
            if self.esp32_worker.connected:
                self.esp32_status_label.setText("CONNECTED")
                self.esp32_status_label.setStyleSheet("font-weight: bold; color: green;")
            else:
                self.esp32_status_label.setText("WAITING...")
                self.esp32_status_label.setStyleSheet("font-weight: bold; color: orange;")
        else:
            self.esp32_status_label.setText("DISCONNECTED")
            self.esp32_status_label.setStyleSheet("font-weight: bold; color: gray;")
        
        # Update video label if frame has changed
        if self.is_streaming and self.processed_frame is not None:
            self.update_video_label()
    
    def initialize(self, robot):
        """Initialize the tab with robot reference"""
        self.robot = robot
        
        # Fill IO signal combo box
        if self.robot:
            self.refresh_io_signals()
            self.refresh_group_signals()
        # Log initialization
        self.log_event("Robot control initialized")
    
    def cleanup_resources(self):
        """Clean up resources before closing"""
        # Stop EGM
        if self.egm_worker.running:
            self.stop_egm()
        
        # Stop ESP32
        if self.esp32_worker.running:
            self.disconnect_esp32()
        
        # Release camera
        if self.camera:
            self.stop_stream()
            self.camera.release()
            self.camera = None 
    
    def refresh_group_signals(self):
        """Refresh group I/O signals from robot controller"""
        if not self.robot:
            self.log_event("Cannot refresh group signals - no robot connection")
            return
            
        try:
            # Clear current list
            self.group_signal_combo.clear()
            self.group_signal_combo.addItem("Select a group signal")
            
            # Get I/O signals from robot
            signals = self.robot.io.search_signals()
            
            if signals.get('status_code') == 200 and 'content' in signals:
                if '_embedded' in signals['content'] and 'resources' in signals['content']['_embedded']:
                    signal_list = signals['content']['_embedded']['resources']
                    
                    # Filter group output signals
                    for signal in signal_list:
                        signal_name = signal.get('name', '')
                        signal_type = signal.get('type', '')
                        
                        if signal_type == 'GO' or signal_type == 'GI':  # Group Output or Group Input
                            self.group_signal_combo.addItem(signal_name)
                    
                    self.log_event(f"Loaded {self.group_signal_combo.count()-1} group signals")
                    
                    # Enable controls if signals are available
                    if self.group_signal_combo.count() > 1:
                        self.write_group_button.setEnabled(True)
                        self.auto_write_group_button.setEnabled(True)
            
        except Exception as e:
            error_msg = f"Failed to refresh group signals: {str(e)}"
            self.log_event(f"Error: {error_msg}")
            self.update_debug_log(f"Error refreshing group signals: {str(e)}\n{traceback.format_exc()}")
    
    def write_gesture_to_group(self):
        """Write current gesture value to selected group signal"""
        if not self.robot:
            self.log_event("Cannot write to group I/O - no robot connection")
            return
            
        signal_name = self.group_signal_combo.currentText()
        if signal_name == "Select a group signal":
            # Only show message if manual button press (not auto-write)
            if not self.auto_write_group_button.isChecked():
                self.log_event("Please select a group signal first")
            return
            
        try:
            # Check if hand is detected - skip if no hand detected
            if self.n_fingers < 0 or self.last_detected_gesture == "Không phát hiện tay":
                return
                
            # Only process for finger counts 0 and 1
            # Also consider special cases like closed fist (which might not be counted correctly)
            is_fist = "nắm đấm" in self.last_detected_gesture.lower() or "fist" in self.last_detected_gesture.lower()
            
            # Process for 0 fingers (closed fist) or 1 finger
            if self.n_fingers == 0 or self.n_fingers == 1 or is_fist:
                # Determine the finger count to use
                # If it's a fist detected but finger count isn't 0, force it to 0
                finger_count = 0 if is_fist else min(self.n_fingers, 1)
                
                # Make sure finger_count is limited to our table size (0-1)
                finger_count = min(finger_count, 1)
                
                # Log the detected gesture and finger count
                self.log_event(f"Processing group gesture: {self.last_detected_gesture}, using finger count: {finger_count}")
                
                # Get corresponding I/O value from table
                group_value = int(self.group_signal_table.item(finger_count, 1).text())
                
                # Write value to robot I/O using our utility method
                success = self.write_signal_value(signal_name, group_value)
                
                # Update status display
                if success:
                    self.group_status_label.setText(f"{signal_name} = {group_value}")
                    self.group_status_label.setStyleSheet("font-weight: bold; color: green;")
            else:
                # Log that we're ignoring this finger count
                self.log_event(f"Finger count {self.n_fingers} outside allowed values (0,1), maintaining previous value")
            
        except Exception as e:
            import traceback
            self.log_event(f"Error writing to group signal: {str(e)}")
            self.update_debug_log(f"Error details: \n{traceback.format_exc()}")
            
            # Update status display for error
            self.group_status_label.setText(f"Error: {str(e)}")
            self.group_status_label.setStyleSheet("font-weight: bold; color: red;")
    
    def on_auto_write_group_changed(self, state):
        """Handle auto-write button state change for group signals"""
        if state == Qt.Checked:
            signal_name = self.group_signal_combo.currentText()
            if signal_name == "Select a group signal":
                self.log_event("Please select a group signal first")
                self.auto_write_group_button.setChecked(False)
            else:
                self.log_event(f"Auto-write enabled for group signal {signal_name}")
                # Update button style for active state
                self.auto_write_group_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        else:
            self.log_event("Auto-write for group signals disabled")
            # Reset button style
            self.auto_write_group_button.setStyleSheet("")
    
    def write_signal_value(self, signal_name, value):
        """Write a value to a signal - similar to io_tab implementation"""
        if not self.robot:
            self.log_event(f"Cannot write to signal {signal_name} - no robot connection")
            return False
            
        try:
            # Log the attempt
            self.log_event(f"Setting signal {signal_name} to {value}...")
            
            # Call RWS API to set the signal value
            result = self.robot.io.set_signal_value(signal_name, value)
            
            if result.get('status_code') in [200, 201, 202, 204]:
                self.log_event(f"Successfully set {signal_name} to {value}")
                return True
            else:
                error_msg = result.get('error', 'Unknown error')
                self.log_event(f"Failed to set signal {signal_name}: {error_msg}")
                return False
                
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            self.log_event(f"Error writing to signal {signal_name}: {str(e)}")
            self.update_debug_log(f"Error details: \n{error_traceback}")
            return False

    def disconnect_camera(self):
        """Disconnect from the camera"""
        try:
            # Stop stream if running
            if self.is_streaming:
                self.stop_stream()
                
            # Release camera
            if self.camera is not None:
                self.camera.release()
                self.camera = None
                
            # Reset video display
            self.video_label.setText("No video feed")
            self.video_label.setStyleSheet("background-color: black; color: white;")
            
            # Update UI
            self.connect_camera_button.setEnabled(True)
            self.disconnect_camera_button.setEnabled(False)
            self.start_stream_button.setEnabled(False)
            self.stop_stream_button.setEnabled(False)
            self.apply_settings_button.setEnabled(False)
            
            self.log_event("Disconnected from camera")
            
        except Exception as e:
            error_msg = f"Failed to disconnect from camera: {str(e)}"
            self.log_event(f"Error: {error_msg}")
            self.update_debug_log(f"Error disconnecting from camera: {str(e)}\n{traceback.format_exc()}")
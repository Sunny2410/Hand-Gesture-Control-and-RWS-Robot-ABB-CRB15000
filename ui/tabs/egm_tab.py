from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
                           QLabel, QLineEdit, QPushButton, QComboBox, 
                           QGroupBox, QCheckBox, QFrame, QGridLayout,
                           QDoubleSpinBox, QSlider, QTabWidget,
                           QSpinBox, QRadioButton, QButtonGroup, QMessageBox,
                           QTextEdit, QSplitter)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QIcon, QColor

import time
import numpy as np
import socket
import traceback
import os
import threading

# Import EGM client
from abb_egm_pyclient.egm_client import EGMClient
from abb_egm_pyclient import DEFAULT_UDP_PORT


class AtomicCounter:
    """Thread-safe counter for EGM sequence numbers"""
    def __init__(self, initial=0):
        self.value = initial
        self._lock = None
        try:
            import threading
            self._lock = threading.Lock()
        except ImportError:
            pass
            
    def inc(self):
        """Increment the counter and return the new value"""
        if self._lock:
            with self._lock:
                self.value += 1
                return self.value
        else:
            self.value += 1
            return self.value
            
    def reset(self):
        """Reset counter to initial value"""
        if self._lock:
            with self._lock:
                self.value = 0
        else:
            self.value = 0


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
        
    def configure(self, port):
        """Configure the EGM client with the specified port"""
        self.port = port
        
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
        """Thread function to continuously send position updates from UI sliders"""
        last_send_time = 0
        
        while self.running:
            try:
                current_time = time.time()
                
                # Gửi lệnh mỗi 50ms (20Hz)
                if (current_time - last_send_time) > 0.05:
                    # Lấy giá trị trực tiếp từ thanh trượt UI
                    if hasattr(self, "get_slider_values"):
                        slider_values = self.get_slider_values()
                        if slider_values:
                            # Gửi giá trị từ thanh trượt
                            self.egm_client.send_planned_frame(
                                slider_values["x"], slider_values["y"], slider_values["z"],
                                slider_values["rx"], slider_values["ry"], slider_values["rz"]
                            )
                            # self.debug_update.emit(f"Sent slider values: {slider_values}")
                    
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


class EGMTab(QWidget):
    """Tab for ABB Externally Guided Motion (EGM) control"""
    
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
        
        # Initialization flag
        self.slider_initialized = False
        
        # Initialize UI
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        # Main layout 
        main_layout = QVBoxLayout(self)
        
        # Create a top and bottom splitter
        self.main_splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(self.main_splitter)
        
        # Top section contains controls
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        self.main_splitter.addWidget(top_widget)
        
        # Connection group
        connection_group = QGroupBox("EGM Connection")
        connection_layout = QFormLayout()
        
        # Port input
        self.port_spinbox = QSpinBox()
        self.port_spinbox.setRange(1024, 65535)
        self.port_spinbox.setValue(DEFAULT_UDP_PORT)
        connection_layout.addRow("UDP Port:", self.port_spinbox)
        
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
        
        # Add advanced options
        advanced_layout = QHBoxLayout()
        
        self.kill_port_button = QPushButton("Release Port")
        self.kill_port_button.setToolTip("Force release the UDP port if it's stuck")
        self.kill_port_button.clicked.connect(self.force_release_port)
        advanced_layout.addWidget(self.kill_port_button)
        
        self.test_port_button = QPushButton("Test Port")
        self.test_port_button.setToolTip("Test if the UDP port can be bound")
        self.test_port_button.clicked.connect(self.test_port_binding)
        advanced_layout.addWidget(self.test_port_button)
        
        self.restart_egm_button = QPushButton("Reset EGM")
        self.restart_egm_button.setToolTip("Reset EGM state and connection")
        self.restart_egm_button.clicked.connect(self.restart_egm)
        advanced_layout.addWidget(self.restart_egm_button)
        
        # Add Reset Sequence button
        self.reset_sequence_button = QPushButton("Reset Sequence")
        self.reset_sequence_button.setToolTip("Reset sequence counter to fix unresponsive commands")
        self.reset_sequence_button.clicked.connect(self.reset_sequence_counter)
        advanced_layout.addWidget(self.reset_sequence_button)
        
        connection_layout.addRow("Advanced:", advanced_layout)
        
        # Status label
        self.status_label = QLabel("Not connected")
        self.status_label.setStyleSheet("font-weight: bold;")
        connection_layout.addRow("Status:", self.status_label)
        
        # Robot state label
        self.robot_state_label = QLabel("Unknown")
        self.robot_state_label.setStyleSheet("font-weight: bold;")
        connection_layout.addRow("Robot State:", self.robot_state_label)
        
        # Apply layout to group
        connection_group.setLayout(connection_layout)
        top_layout.addWidget(connection_group)
        
        # Cartesian control section
        cartesian_group = QGroupBox("Cartesian Control")
        cartesian_layout = QHBoxLayout()  # Changed to horizontal layout
        
        # Left side: Current position
        current_position_group = QGroupBox("Current Position")
        current_position_layout = QGridLayout()
        
        # Position labels
        current_position_layout.addWidget(QLabel("X:"), 0, 0)
        self.x_label = QLabel("0.0 mm")
        self.x_label.setStyleSheet("font-weight: bold;")
        current_position_layout.addWidget(self.x_label, 0, 1)
        
        current_position_layout.addWidget(QLabel("Y:"), 1, 0)
        self.y_label = QLabel("0.0 mm")
        self.y_label.setStyleSheet("font-weight: bold;")
        current_position_layout.addWidget(self.y_label, 1, 1)
        
        current_position_layout.addWidget(QLabel("Z:"), 2, 0)
        self.z_label = QLabel("0.0 mm")
        self.z_label.setStyleSheet("font-weight: bold;")
        current_position_layout.addWidget(self.z_label, 2, 1)
        
        current_position_layout.addWidget(QLabel("Rx:"), 3, 0)
        self.rx_label = QLabel("0.0°")
        self.rx_label.setStyleSheet("font-weight: bold;")
        current_position_layout.addWidget(self.rx_label, 3, 1)
        
        current_position_layout.addWidget(QLabel("Ry:"), 4, 0)
        self.ry_label = QLabel("0.0°")
        self.ry_label.setStyleSheet("font-weight: bold;")
        current_position_layout.addWidget(self.ry_label, 4, 1)
        
        current_position_layout.addWidget(QLabel("Rz:"), 5, 0)
        self.rz_label = QLabel("0.0°")
        self.rz_label.setStyleSheet("font-weight: bold;")
        current_position_layout.addWidget(self.rz_label, 5, 1)

        # Apply layout to group
        current_position_group.setLayout(current_position_layout)
        cartesian_layout.addWidget(current_position_group)
        
        # Right side: Target cartesian values
        target_group = QGroupBox("Target Position")
        target_layout = QGridLayout()
        
        # Position inputs with sliders
        target_layout.addWidget(QLabel("X:"), 0, 0)
        self.x_spinbox = QDoubleSpinBox()
        self.x_spinbox.setRange(-2000, 2000)
        self.x_spinbox.setSuffix(" mm")
        self.x_spinbox.setSingleStep(10.0)
        self.x_spinbox.setDecimals(2)
        target_layout.addWidget(self.x_spinbox, 0, 1)
        
        self.x_slider = QSlider(Qt.Horizontal)
        self.x_slider.setRange(-2000, 2000)
        self.x_slider.setSingleStep(1)
        self.x_slider.setPageStep(10)
        target_layout.addWidget(self.x_slider, 0, 2)
        
        target_layout.addWidget(QLabel("Y:"), 1, 0)
        self.y_spinbox = QDoubleSpinBox()
        self.y_spinbox.setRange(-2000, 2000)
        self.y_spinbox.setSuffix(" mm")
        self.y_spinbox.setSingleStep(10.0)
        self.y_spinbox.setDecimals(2)
        target_layout.addWidget(self.y_spinbox, 1, 1)
        
        self.y_slider = QSlider(Qt.Horizontal)
        self.y_slider.setRange(-2000, 2000)
        self.y_slider.setSingleStep(1)
        self.y_slider.setPageStep(10)
        target_layout.addWidget(self.y_slider, 1, 2)
        
        target_layout.addWidget(QLabel("Z:"), 2, 0)
        self.z_spinbox = QDoubleSpinBox()
        self.z_spinbox.setRange(-2000, 2000)
        self.z_spinbox.setSuffix(" mm")
        self.z_spinbox.setSingleStep(10.0)
        self.z_spinbox.setDecimals(2)
        target_layout.addWidget(self.z_spinbox, 2, 1)
        
        self.z_slider = QSlider(Qt.Horizontal)
        self.z_slider.setRange(-2000, 2000)
        self.z_slider.setSingleStep(1)
        self.z_slider.setPageStep(10)
        target_layout.addWidget(self.z_slider, 2, 2)
        
        # Orientation inputs with sliders
        target_layout.addWidget(QLabel("Rx:"), 3, 0)
        self.rx_spinbox = QDoubleSpinBox()
        self.rx_spinbox.setRange(-180, 180)
        self.rx_spinbox.setSuffix("°")
        self.rx_spinbox.setSingleStep(5.0)
        self.rx_spinbox.setDecimals(2)
        target_layout.addWidget(self.rx_spinbox, 3, 1)
        
        self.rx_slider = QSlider(Qt.Horizontal)
        self.rx_slider.setRange(-180, 180)
        self.rx_slider.setSingleStep(1)
        self.rx_slider.setPageStep(5)
        target_layout.addWidget(self.rx_slider, 3, 2)
        
        target_layout.addWidget(QLabel("Ry:"), 4, 0)
        self.ry_spinbox = QDoubleSpinBox()
        self.ry_spinbox.setRange(-180, 180)
        self.ry_spinbox.setSuffix("°")
        self.ry_spinbox.setSingleStep(5.0)
        self.ry_spinbox.setDecimals(2)
        target_layout.addWidget(self.ry_spinbox, 4, 1)
        
        self.ry_slider = QSlider(Qt.Horizontal)
        self.ry_slider.setRange(-180, 180)
        self.ry_slider.setSingleStep(1)
        self.ry_slider.setPageStep(5)
        target_layout.addWidget(self.ry_slider, 4, 2)
        
        target_layout.addWidget(QLabel("Rz:"), 5, 0)
        self.rz_spinbox = QDoubleSpinBox()
        self.rz_spinbox.setRange(-180, 180)
        self.rz_spinbox.setSuffix("°")
        self.rz_spinbox.setSingleStep(5.0)
        self.rz_spinbox.setDecimals(2)
        target_layout.addWidget(self.rz_spinbox, 5, 1)
        
        self.rz_slider = QSlider(Qt.Horizontal)
        self.rz_slider.setRange(-180, 180)
        self.rz_slider.setSingleStep(1)
        self.rz_slider.setPageStep(5)
        target_layout.addWidget(self.rz_slider, 5, 2)
        
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
        

        # Apply layout to group
        target_group.setLayout(target_layout)
        cartesian_layout.addWidget(target_group)
        
        # Apply cartesian layout to group
        cartesian_group.setLayout(cartesian_layout)
        top_layout.addWidget(cartesian_group)
        
        # Add a placeholder for event log
        log_group = QGroupBox("EGM Events")
        log_layout = QVBoxLayout()
        
        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        self.event_log.setMinimumHeight(60)
        log_layout.addWidget(self.event_log)
        
        # Apply layout to group
        log_group.setLayout(log_layout)
        top_layout.addWidget(log_group)
        
        # Bottom section contains debug log
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        self.main_splitter.addWidget(bottom_widget)
        
        # Debug log section
        debug_group = QGroupBox("EGM Debug")
        debug_layout = QVBoxLayout()
        
        self.debug_log = QTextEdit()
        self.debug_log.setReadOnly(True)
        debug_layout.addWidget(self.debug_log)
        
        # Clear button
        self.clear_debug_button = QPushButton("Clear Debug Log")
        self.clear_debug_button.clicked.connect(self.clear_debug_log)
        debug_layout.addWidget(self.clear_debug_button)
        
        # Apply layout to group
        debug_group.setLayout(debug_layout)
        bottom_layout.addWidget(debug_group)
        
        # Set splitter sizes - 70% for controls, 30% for debug
        self.main_splitter.setSizes([700, 300])
    
    def initialize(self, robot):
        """Initialize the tab with robot reference"""
        self.robot = robot
        
        # Pass reference to get_slider_values to worker
        self.egm_worker.get_slider_values = self.get_slider_values
        
        # Check if ABB EGM module is available by checking version info and RWS capabilities
        if self.robot is not None:
            try:
                capabilities = self.robot.get_capabilities()
                if 'egm' in capabilities:
                    self.log_event("ABB EGM module detected")
                    self.update_debug_log("ABB EGM module detected on controller")
                else:
                    self.log_event("Warning: ABB EGM module might not be available")
                    self.update_debug_log("Warning: ABB EGM module might not be available on controller")
            except Exception as e:
                self.log_event("Warning: Couldn't check controller capabilities")
                self.update_debug_log(f"Warning: Couldn't check controller capabilities: {str(e)}")
    
    def start_egm(self):
        """Start EGM communication"""
        try:
            # Configure EGM worker
            port = self.port_spinbox.value()
            self.egm_worker.configure(port)
            
            # Start worker thread
            self.egm_worker.start()
            
            # Update UI
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.port_spinbox.setEnabled(False)
            
            self.log_event(f"Started EGM on port {port}")
            self.update_debug_log(f"Starting EGM worker thread on port {port}")
            
        except Exception as e:
            error_msg = f"Failed to start EGM: {str(e)}"
            self.log_event(f"Error: {error_msg}")
            self.update_debug_log(f"Error starting EGM: {str(e)}\n{traceback.format_exc()}")
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
            self.port_spinbox.setEnabled(True)
            
            self.log_event("Stopped EGM")
            
        except Exception as e:
            error_msg = f"Failed to stop EGM: {str(e)}"
            self.log_event(f"Error: {error_msg}")
            self.update_debug_log(f"Error stopping EGM: {str(e)}\n{traceback.format_exc()}")
            QMessageBox.critical(self, "EGM Error", error_msg)
    
    @pyqtSlot(dict)
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
    
    @pyqtSlot(str)
    def update_status(self, status):
        """Update status label"""
        self.status_label.setText(status)
        self.log_event(status)
    
    @pyqtSlot(str)
    def handle_error(self, error_msg):
        """Handle error from worker thread"""
        self.log_event(f"Error: {error_msg}")
    
    @pyqtSlot(bool)
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
                self.port_spinbox.setEnabled(True)
    
    @pyqtSlot(str)
    def update_debug_log(self, message):
        """Add message to debug log"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        self.debug_log.append(f"[{timestamp}] {message}")
    
    def clear_debug_log(self):
        """Clear the debug log"""
        self.debug_log.clear()
        self.update_debug_log("Debug log cleared")


    def log_event(self, message):
        """Add message to event log"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        self.event_log.append(f"[{timestamp}] {message}")
            
    def update_ui(self):
        """Update UI elements - called periodically by main window"""
        # Check if EGM is running and update connection status
        if self.egm_worker.running and hasattr(self.egm_worker, 'egm_client') and self.egm_worker.egm_client:
            # Update connection state
            self.robot_state_label.setText("CONNECTED")
            self.robot_state_label.setStyleSheet("font-weight: bold; color: green;")
            
            # Update sliders with current position if they don't have focus
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

    def force_release_port(self):
        """Force release the UDP port by killing any socket using it"""
        try:
            port = self.port_spinbox.value()
            self.update_debug_log(f"Attempting to force release port {port}")
            
            # Create a temporary socket to try to bind to the port
            temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            temp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Try to bind with both options
            try:
                temp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except (AttributeError, OSError):
                pass
                
            try:
                temp_socket.bind(('', port))
                self.update_debug_log(f"Successfully bound to port {port}")
                
                # Now close it properly
                temp_socket.close()
                self.update_debug_log(f"Port {port} has been released")
                self.log_event(f"Port {port} successfully released")
                
            except OSError as e:
                self.update_debug_log(f"Failed to bind to port {port}: {str(e)}")
                temp_socket.close()
                
                # On Windows, try using netstat to find the process
                if os.name == 'nt':
                    self.update_debug_log("Attempting to identify process using the port on Windows")
                    try:
                        import subprocess
                        result = subprocess.run(f'netstat -ano | findstr :{port}', 
                                              capture_output=True, text=True, shell=True)
                        self.update_debug_log(f"Netstat result: {result.stdout}")
                        self.log_event(f"Port {port} is in use. Check debug log for details.")
                    except Exception as e:
                        self.update_debug_log(f"Error running netstat: {str(e)}")
                
                # On Linux/Mac
                else:
                    self.update_debug_log("Attempting to identify process using the port on Unix")
                    try:
                        import subprocess
                        result = subprocess.run(f'lsof -i :{port}', 
                                              capture_output=True, text=True, shell=True)
                        self.update_debug_log(f"lsof result: {result.stdout}")
                        self.log_event(f"Port {port} is in use. Check debug log for details.")
                    except Exception as e:
                        self.update_debug_log(f"Error running lsof: {str(e)}")
                
        except Exception as e:
            self.update_debug_log(f"Error in force_release_port: {str(e)}\n{traceback.format_exc()}")
            self.log_event(f"Error releasing port: {str(e)}")
            
    def test_port_binding(self):
        """Test if we can bind to the UDP port"""
        try:
            port = self.port_spinbox.value()
            self.update_debug_log(f"Testing binding to port {port}")
            
            # Try standard socket creation first
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            test_socket.settimeout(1)
            
            try:
                test_socket.bind(('', port))
                self.update_debug_log(f"Successfully bound to port {port}")
                self.log_event(f"Port {port} is available and can be bound")
                test_socket.close()
                return True
            except OSError as e:
                self.update_debug_log(f"Failed to bind to port {port}: {str(e)}")
                self.log_event(f"Could not bind to port {port}: {str(e)}")
                test_socket.close()
                return False
            
        except Exception as e:
            self.update_debug_log(f"Error in test_port_binding: {str(e)}\n{traceback.format_exc()}")
            self.log_event(f"Error testing port: {str(e)}")
            return False

    def restart_egm(self):
        """Attempt to reset EGM state by restarting the connection"""
        try:
            self.update_debug_log("Attempting to reset EGM state")
            
            # First stop EGM
            if self.egm_worker.running:
                self.update_debug_log("Stopping current EGM connection")
                self.stop_egm()
                time.sleep(1)  # Give time for cleanup
            
            # Check if robot connection is available
            if self.robot:
                try:
                    self.update_debug_log("Sending reset commands to robot controller (if supported)")
                    # This would contain code specific to your robot controller's API
                    # For example, if there's a method to reset EGM or restart RAPID tasks
                except Exception as e:
                    self.update_debug_log(f"Error sending robot controller commands: {str(e)}")
            
            # Wait a moment to ensure resources are released
            time.sleep(1)
            
            # Start EGM again
            self.update_debug_log("Starting new EGM connection")
            self.start_egm()
            
            # Show message to user
            QMessageBox.information(self, "EGM Reset", 
                                  "EGM connection has been reset.\n\n"
                                  "If robot is in STOPPED state, you still need to restart the RAPID program on the robot controller.")
            
        except Exception as e:
            self.update_debug_log(f"Error during EGM reset: {str(e)}\n{traceback.format_exc()}")
            QMessageBox.critical(self, "Reset Error", f"Failed to reset EGM: {str(e)}") 

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
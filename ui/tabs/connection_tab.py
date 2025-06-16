from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
                           QLabel, QLineEdit, QPushButton, QComboBox, 
                           QGroupBox, QCheckBox, QFrame, QGridLayout)
from PyQt5.QtCore import Qt, pyqtSignal, QSettings
from PyQt5.QtGui import QFont, QIcon
class ConnectionTab(QWidget):
    """Tab for robot connection settings and controls"""
    
    def __init__(self, connect_callback):
        super().__init__()
        
        # Store the callback function
        self.connect_callback = connect_callback
        
        # Initialize UI
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Connection settings group
        connection_group = QGroupBox("Connection Settings")
        connection_layout = QFormLayout()
        
        # Host field
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("192.168.125.1:80")
        connection_layout.addRow("Host:", self.host_input)
        
        # Protocol selection
        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(["https://", "http://"])
        connection_layout.addRow("Protocol:", self.protocol_combo)
        
        # Username field
        self.username_input = QLineEdit()
        self.username_input.setText("Default User")
        connection_layout.addRow("Username:", self.username_input)
        
        # Password field
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setText("robotics")
        connection_layout.addRow("Password:", self.password_input)
        
        # Save password checkbox
        self.save_password_check = QCheckBox("Save password")
        self.save_password_check.setStyleSheet("""
            QCheckBox::indicator {
                width: 22px;
                height: 22px;
                border: 2px solid #555;
                border-radius: 4px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #3a7ab8;
                border: 2px solid #3a7ab8;
            }
        """)
        connection_layout.addRow("", self.save_password_check)
        
        # Apply to connection group
        connection_group.setLayout(connection_layout)
        main_layout.addWidget(connection_group)
        
        # Recent connections group
        recent_group = QGroupBox("Recent Connections")
        recent_layout = QVBoxLayout()
        
        # Recent connections list (could be a combo box or list widget)
        self.recent_combo = QComboBox()
        self.recent_combo.setPlaceholderText("Select a recent connection")
        self.recent_combo.currentIndexChanged.connect(self.load_recent_connection)
        recent_layout.addWidget(self.recent_combo)
        
        # Apply to recent group
        recent_group.setLayout(recent_layout)
        main_layout.addWidget(recent_group)
        
        # Connection status group
        status_group = QGroupBox("Connection Status")
        status_layout = QGridLayout()
        
        # Status indicator
        self.status_label = QLabel("Not Connected")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        status_layout.addWidget(QLabel("Status:"), 0, 0)
        status_layout.addWidget(self.status_label, 0, 1)
        
        # Controller version (shown when connected)
        self.controller_version_label = QLabel("N/A")
        status_layout.addWidget(QLabel("Controller:"), 1, 0)
        status_layout.addWidget(self.controller_version_label, 1, 1)
        
        # RobotWare version (shown when connected)
        self.robotware_version_label = QLabel("N/A")
        status_layout.addWidget(QLabel("RobotWare:"), 2, 0)
        status_layout.addWidget(self.robotware_version_label, 2, 1)
        
                # Controller version (shown when connected)
        self.controller_state_label = QLabel("N/A")
        status_layout.addWidget(QLabel("Controller State:"), 3, 0)
        status_layout.addWidget(self.controller_state_label, 3, 1)
        
        # RobotWare version (shown when connected)
        self.motor_state_label = QLabel("N/A")
        status_layout.addWidget(QLabel("Motor State:"), 4, 0)
        status_layout.addWidget(self.motor_state_label, 4, 1)

        # RobotWare version (shown when connected)
        self.rapid_state_label = QLabel("N/A")
        status_layout.addWidget(QLabel("RAPID State:"), 5, 0)
        status_layout.addWidget(self.rapid_state_label, 5, 1)



        # Apply to status group
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)
        
        # Create horizontal layout for buttons
        button_layout = QHBoxLayout()
        
        # Connect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.setIcon(QIcon("ui/resources/connect.png"))
        self.connect_button.clicked.connect(self.on_connect_click)
        button_layout.addWidget(self.connect_button)
        
        # Disconnect button (disabled initially)
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.setIcon(QIcon("ui/resources/disconnect.png"))
        self.disconnect_button.setEnabled(False)
        self.disconnect_button.clicked.connect(self.on_disconnect_click)
        button_layout.addWidget(self.disconnect_button)
        
        # Add buttons to main layout
        main_layout.addLayout(button_layout)
        
        # Add stretch to push everything to the top
        main_layout.addStretch(1)
        
        # Load recent connections
        self.load_recent_connections()
        
    def on_connect_click(self):
        """Handle connect button click"""
        # Get connection information
        host = self.host_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text()
        protocol = self.protocol_combo.currentText()
        
        # Validate inputs
        if not host:
            self.status_label.setText("Error: Host is required")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            return
            
        if not username:
            self.status_label.setText("Error: Username is required")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            return
        
        # Update status
        self.status_label.setText("Connecting...")
        self.status_label.setStyleSheet("color: orange; font-weight: bold;")
        
        # Call the connect callback
        success = self.connect_callback(host, username, password, protocol)
        
        # If connection was successful, save to recent connections
        if success:
            self.save_to_recent_connections(host, username, password if self.save_password_check.isChecked() else "")
        
    def on_disconnect_click(self):
        """Handle disconnect button click"""
        # Will be connected to parent's disconnect function
        pass
        
    def set_connected(self, connected):
        """Update UI to reflect connection status"""
        if connected:
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)
            
            # Disable input fields
            self.host_input.setEnabled(False)
            self.username_input.setEnabled(False)
            self.password_input.setEnabled(False)
            self.protocol_combo.setEnabled(False)
            self.recent_combo.setEnabled(False)
        else:
            self.status_label.setText("Not Connected")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.connect_button.setEnabled(True)
            self.disconnect_button.setEnabled(False)
            
            # Enable input fields
            self.host_input.setEnabled(True)
            self.username_input.setEnabled(True)
            self.password_input.setEnabled(True)
            self.protocol_combo.setEnabled(True)
            self.recent_combo.setEnabled(True)
            
            # Reset controller information
            self.controller_version_label.setText("N/A")
            self.robotware_version_label.setText("N/A")
            self.controller_state_label.setText("N/A")
            self.motor_state_label.setText("N/A")
            self.rapid_state_label.setText("N/A")
    
    def set_controller_info(self, controller_version, robotware_version, controller_state, motor_state, rapid_state):
        """Update controller information"""
        print("Inside set_controller_info method")
        
        # Check if labels are defined
        if hasattr(self, 'controller_version_label'):
            self.controller_version_label.setText(controller_version)
        else:
            print("Error: controller_version_label is not defined")
            
        if hasattr(self, 'robotware_version_label'):
            self.robotware_version_label.setText(robotware_version)
        else:
            print("Error: robotware_version_label is not defined")
            
        if hasattr(self, 'controller_state_label'):
            self.controller_state_label.setText(controller_state)
        else:
            print("Error: controller_state_label is not defined")
            
        if hasattr(self, 'motor_state_label'):
            self.motor_state_label.setText(motor_state)
        else:
            print("Error: motor_state_label is not defined")
                        
        if hasattr(self, 'rapid_state_label'):
            self.rapid_state_label.setText(rapid_state)
        else:
            print("Error: rapid_state_label is not defined")
            
        print("Controller information update attempt completed")
    
    def load_recent_connections(self):
        """Load recent connections from settings"""
        settings = QSettings()
        size = settings.beginReadArray("recent_connections")
        
        # Clear existing items
        self.recent_combo.clear()
        
        # Add placeholder
        self.recent_combo.addItem("Select a recent connection", None)
        
        # Add saved connections
        for i in range(size):
            settings.setArrayIndex(i)
            host = settings.value("host")
            username = settings.value("username")
            # Display as "username@host"
            self.recent_combo.addItem(f"{username}@{host}", {
                "host": host,
                "username": username,
                "password": settings.value("password", ""),
                "protocol": settings.value("protocol", "https://")
            })
            
        settings.endArray()
    
    def save_to_recent_connections(self, host, username, password):
        """Save connection to recent connections"""
        settings = QSettings()
        
        # Load existing connections
        connections = []
        size = settings.beginReadArray("recent_connections")
        for i in range(size):
            settings.setArrayIndex(i)
            connections.append({
                "host": settings.value("host"),
                "username": settings.value("username"),
                "password": settings.value("password", ""),
                "protocol": settings.value("protocol", "https://")
            })
        settings.endArray()
        
        # Check if this connection already exists
        for conn in connections:
            if conn["host"] == host and conn["username"] == username:
                # Update password if needed
                if password:
                    conn["password"] = password
                # Move to top
                connections.remove(conn)
                connections.insert(0, conn)
                break
        else:
            # Add new connection to top
            connections.insert(0, {
                "host": host,
                "username": username,
                "password": password,
                "protocol": self.protocol_combo.currentText()
            })
        
        # Limit to 10 recent connections
        connections = connections[:10]
        
        # Save back to settings
        settings.beginWriteArray("recent_connections", len(connections))
        for i, conn in enumerate(connections):
            settings.setArrayIndex(i)
            settings.setValue("host", conn["host"])
            settings.setValue("username", conn["username"])
            settings.setValue("password", conn["password"])
            settings.setValue("protocol", conn["protocol"])
        settings.endArray()
        
        # Reload the combo box
        self.load_recent_connections()
    
    def load_recent_connection(self, index):
        """Load connection data from selected recent connection"""
        if index <= 0:  # Skip placeholder item
            return
            
        # Get connection data
        conn_data = self.recent_combo.itemData(index)
        if not conn_data:
            return
            
        # Fill input fields
        self.host_input.setText(conn_data["host"])
        self.username_input.setText(conn_data["username"])
        self.password_input.setText(conn_data["password"])
        
        # Set protocol
        protocol_index = self.protocol_combo.findText(conn_data["protocol"])
        if protocol_index >= 0:
            self.protocol_combo.setCurrentIndex(protocol_index)
    
    def set_credentials(self, host, username, password, protocol):
        """Set connection credentials"""
        self.host_input.setText(host)
        self.username_input.setText(username)
        self.password_input.setText(password)
        
        # Set protocol
        protocol_index = self.protocol_combo.findText(protocol)
        if protocol_index >= 0:
            self.protocol_combo.setCurrentIndex(protocol_index)
    
    def get_credentials(self):
        """Get current connection credentials"""
        return (
            self.host_input.text().strip(),
            self.username_input.text().strip(),
            self.password_input.text(),
            self.protocol_combo.currentText()
        )
    
    def update_controller_state(self, controller_state, motor_state):
        """Update controller state information - now updates states independently"""
        # Only update controller_state if provided
        if controller_state is not None and hasattr(self, 'controller_state_label'):
            self.controller_state_label.setText(controller_state)
            
        # Only update motor_state if provided  
        if motor_state is not None and hasattr(self, 'motor_state_label'):
            self.motor_state_label.setText(motor_state)
            
            # Update colors based on states
            if motor_state == "Running":
                self.motor_state_label.setStyleSheet("color: green; font-weight: bold;")
            else:
                self.motor_state_label.setStyleSheet("color: red; font-weight: bold;")
        
    def update_motor_state(self, motor_state):
        """Update just the motor state field"""
        if hasattr(self, 'motor_state_label'):
            self.motor_state_label.setText(motor_state)
            
            # Update colors based on states
            if motor_state == "Running":
                self.motor_state_label.setStyleSheet("color: green; font-weight: bold;")
            else:
                self.motor_state_label.setStyleSheet("color: red; font-weight: bold;")
                
    def update_operation_mode(self, operation_mode):
        """Update just the operation mode field"""
        if hasattr(self, 'controller_state_label'):
            self.controller_state_label.setText(operation_mode)
            
    def update_rapid_state(self, rapid_state):
        """Update just the RAPID state field"""
        if hasattr(self, 'rapid_state_label'):
            self.rapid_state_label.setText(rapid_state)
            
            # Update color based on state
            if rapid_state == "Running":
                self.rapid_state_label.setStyleSheet("color: green; font-weight: bold;")
            elif rapid_state == "Stopped":
                self.rapid_state_label.setStyleSheet("color: red; font-weight: bold;")
            else:
                self.rapid_state_label.setStyleSheet("color: black; font-weight: bold;")

    def get_operation_mode(self):
        """Get the current operation mode displayed in the UI"""
        if hasattr(self, 'controller_state_label'):
            return self.controller_state_label.text()
        return "Unknown"

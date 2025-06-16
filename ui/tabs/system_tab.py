from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
                           QLabel, QLineEdit, QPushButton, QComboBox, 
                           QGroupBox, QCheckBox, QFrame, QGridLayout,
                           QTableWidget, QTableWidgetItem, QHeaderView,
                           QTabWidget, QSplitter, QTextEdit, QListWidget,
                           QSpinBox, QRadioButton, QButtonGroup, QMessageBox,
                           QFileDialog, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon

class SystemTab(QWidget):
    """Tab for robot system control and management"""
    
    def __init__(self):
        super().__init__()
        
        # Store robot reference
        self.robot = None
        
        # Disable updates until initialized
        self.initialized = False
        
        # Initialize UI
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI components"""
        layout = QVBoxLayout(self)
        
        # Place Current User and RMPP Privileges in the same row
        top_row_layout = QHBoxLayout()
        
        # Current user info
        user_info_group = QGroupBox("Current User")
        user_info_layout = QFormLayout()
        
        # Username
        self.current_username_label = QLabel("Unknown")
        user_info_layout.addRow("Username:", self.current_username_label)
        
        # Application
        self.current_app_label = QLabel("Unknown")
        user_info_layout.addRow("Application:", self.current_app_label)
        
        # Location
        self.current_location_label = QLabel("Unknown")
        user_info_layout.addRow("Location:", self.current_location_label)
        
        # RMPP info
        self.current_rmpp_label = QLabel("Unknown")
        user_info_layout.addRow("RMPP Privilege:", self.current_rmpp_label)
        
        # Apply layout to group
        user_info_group.setLayout(user_info_layout)
        top_row_layout.addWidget(user_info_group)
        
        # Set RMPP privileges
        rmpp_group = QGroupBox("Set RMPP Privileges")
        rmpp_layout = QHBoxLayout()
        
        # Privilege selection
        self.privilege_combo = QComboBox()
        self.privilege_combo.addItems(["modify", "exec"])
        rmpp_layout.addWidget(self.privilege_combo)
        
        # Set button
        self.set_rmpp_button = QPushButton("Set Privilege")
        self.set_rmpp_button.clicked.connect(self.on_set_rmpp_click)
        rmpp_layout.addWidget(self.set_rmpp_button)
        
        # Apply layout to group
        rmpp_group.setLayout(rmpp_layout)
        top_row_layout.addWidget(rmpp_group)
        
        # Add top row to main layout
        layout.addLayout(top_row_layout)
        
        # Register user
        register_group = QGroupBox("Register User")
        register_layout = QFormLayout()
        
        # Username with default value
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        register_layout.addRow("Username:", self.username_input)
        
        # Application with default value
        self.application_input = QLineEdit()
        self.application_input.setPlaceholderText("Enter application name")
        register_layout.addRow("Application:", self.application_input)
        
        # Location with default value
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("Enter location")
        register_layout.addRow("Location:", self.location_input)
        
        # Register button
        self.register_button = QPushButton("Register User")
        self.register_button.clicked.connect(self.on_register_user_click)
        register_layout.addRow("", self.register_button)
        
        # Apply layout to group
        register_group.setLayout(register_layout)
        layout.addWidget(register_group)
        
        # Add a placeholder for event log
        log_group = QGroupBox("User Management Events")
        log_layout = QVBoxLayout()
        
        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        self.event_log.setStyleSheet("background-color: #F0F0F0; border: 1px solid #CCC; padding: 8px; font-family: monospace;")
        self.event_log.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.event_log.setMinimumHeight(120)
        log_layout.addWidget(self.event_log)
        
        # Apply layout to group
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

    def initialize(self, robot):
        """Initialize with robot reference and load system info"""
        self.robot = robot
        

        self.username_input.setText("Default User")
        self.application_input.setText("RWS Client")
        self.location_input.setText("Local")
        # Load initial values        
        # Set initialized flag
        self.initialized = True
        self.log_event("System tab initialized")
    
    def set_initial_values(self, initial_values):
        if not initial_values:
            return
            
        try:
            # Extract controller state from panel data
            if '/users/rmmp' in initial_values:
                rmmp_resp = initial_values['/users/rmmp']
                if rmmp_resp.get('status_code') == 200:
                    # Extract ctrlstate from the response structure
                    privilege = rmmp_resp.get('content', {}).get('state', [{}])[0].get('privilege', 'Unknown')
                    self.current_rmpp_label.setText(privilege)
 
        except Exception as e:
            self.log_event(f"Error setting initial values: {str(e)}")



    
    def update_ui(self):
        """Periodic UI update"""
        if not self.robot or not self.initialized:
            return
        
        # No need for periodic updates in this tab
        pass
    
    def on_set_rmpp_click(self):
        """Set RMPP privileges"""
        if not self.robot:
            return
            
        try:
            # Get privilege
            privilege = self.privilege_combo.currentText()
            
            self.log_event(f"Setting RMPP privilege to {privilege}...")
            result = self.robot.user.set_rmmp_user_info(privilege)
            
            if result.get('status_code') in [200, 202]:
                self.log_event(f"RMPP privilege set to {privilege}")
            else:
                self.log_event(f"Error setting RMPP privilege: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.log_event(f"Error setting RMPP privilege: {str(e)}")
    
    def on_register_user_click(self):
        """Register user"""
        if not self.robot:
            return
            
        try:
            # Get user info
            username = self.username_input.text().strip()
            application = self.application_input.text().strip()
            location = self.location_input.text().strip()
            
            if not username or not application:
                self.log_event("Error: All fields are required")
                return
                
            self.log_event(f"Registering user {username}...")
            result = self.robot.user.set_local_user(username, application, location, local_key='123456789')
            
            if result.get('status_code') in [200, 201, 204]:
                self.log_event(f"User {username} registered successfully")
                
                # Update current user info
                self.current_username_label.setText(username)
                self.current_app_label.setText(application)
                self.current_location_label.setText(location)
            else:
                self.log_event(f"Error registering user: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.log_event(f"Error registering user: {str(e)}")

    def log_event(self, message):
        """Add a message to the event log"""
        import time
        timestamp = time.strftime("%H:%M:%S")
        self.event_log.append(f"[{timestamp}] {message}")

    def update_rmpp_user_info(self, rmmp_user_info):
        """Update RMPP user info"""
        if rmmp_user_info !='0' : 
            self.current_rmpp_label.setText("Privilege")
            self.log_event(f"Updated RMPP privilege: Privilege")
        else:
            self.current_rmpp_label.setText("None")
            self.log_event(f"Updated RMPP privilege: None")

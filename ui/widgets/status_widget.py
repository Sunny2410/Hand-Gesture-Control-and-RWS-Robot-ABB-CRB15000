from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon

class StatusWidget(QWidget):
    """Widget for displaying status information in the status bar"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize UI
        self.init_ui()
        
        # Setup timer for clock updates
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)  # Update every second
    
    def init_ui(self):
        """Initialize the UI components"""
        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Connection status
        layout.addWidget(QLabel("Status:"))
        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        # Separator
        separator1 = QLabel("|")
        separator1.setStyleSheet("color: #CCCCCC;")
        layout.addWidget(separator1)
        
        # Controller time
        layout.addWidget(QLabel("Controller Time:"))
        self.controller_time_label = QLabel("--:--:--")
        layout.addWidget(self.controller_time_label)
        
        # Separator
        separator2 = QLabel("|")
        separator2.setStyleSheet("color: #CCCCCC;")
        layout.addWidget(separator2)
        
        # User info
        layout.addWidget(QLabel("User:"))
        self.user_label = QLabel("Not logged in")
        layout.addWidget(self.user_label)
        
        # Separator
        separator3 = QLabel("|")
        separator3.setStyleSheet("color: #CCCCCC;")
        layout.addWidget(separator3)
        
        # Local time
        self.local_time_label = QLabel()
        self.update_clock()  # Initialize with current time
        layout.addWidget(self.local_time_label)
        
        # Add stretch to push everything to the left
        layout.addStretch(1)
    
    def set_status(self, status: str, color: str = "black"):
        """Set the connection status
        
        Args:
            status: Status text to display
            color: Color name for the status text
        """
        self.status_label.setText(status)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
    
    def set_user(self, username: str):
        """Set the current user
        
        Args:
            username: Username to display
        """
        self.user_label.setText(username)
    
    def set_controller_time(self, time_str: str):
        """Set the controller time
        
        Args:
            time_str: Time string to display
        """
        self.controller_time_label.setText(time_str)
    
    def update_clock(self):
        """Update the local time display"""
        import time
        current_time = time.strftime("%H:%M:%S")
        self.local_time_label.setText(f"Local Time: {current_time}")
    
    def update_controller_time(self):
        """Update the controller time from the robot (placeholder)"""
        import time
        # In a real implementation, this would get the time from the robot
        # For now, we just use the local time
        current_time = time.strftime("%H:%M:%S")
        self.controller_time_label.setText(current_time) 
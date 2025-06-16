from PyQt5.QtWidgets import QSplashScreen, QLabel, QProgressBar, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QPixmap, QColor, QPainter, QFont

class SplashScreen(QSplashScreen):
    """Custom splash screen with progress bar and version information"""
    
    def __init__(self):
        # Create pixmap for splash screen and do all painting before creating QSplashScreen
        pixmap = self._create_splash_pixmap()
        super().__init__(pixmap)
        
        # Create widget to hold progress bar and labels
        self._setup_ui()
        
        # Setup animation
        self.counter = 0
        self._setup_timer()
    
    def _create_splash_pixmap(self):
        """Create and return a painted pixmap for the splash screen"""
        pixmap = QPixmap(500, 300)
        pixmap.fill(Qt.white)
        
        # Create painter for the pixmap
        painter = QPainter(pixmap)
        
        # Fill background
        painter.fillRect(0, 0, 500, 300, QColor('#FFFFFF'))
        
        # Add application title
        painter.setPen(QColor('#3874BA'))
        font = QFont("Arial", 24, QFont.Bold)
        painter.setFont(font)
        painter.drawText(50, 80, "ABB Robot Control")
        
        # Add application subtitle
        painter.setPen(QColor('#666666'))
        font = QFont("Arial", 12)
        painter.setFont(font)
        painter.drawText(50, 110, "Comprehensive Robot Control Interface")
        
        # Add a decorative line
        painter.setPen(QColor('#3874BA'))
        painter.drawLine(50, 130, 450, 130)
        
        # Add logo placeholder
        painter.drawText(350, 40, "LOGO")
        painter.drawRect(330, 20, 100, 40)
        
        # End painter before returning pixmap
        painter.end()
        return pixmap
    
    def _setup_ui(self):
        """Set up the UI components for the splash screen"""
        # Create widget to hold progress bar and labels
        self.layout_widget = QWidget(self)
        layout = QVBoxLayout(self.layout_widget)
        
        # Version label
        self.version_label = QLabel("v1.0.0", self)
        self.version_label.setStyleSheet("color: #666666; font-size: 10pt;")
        self.version_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        layout.addWidget(self.version_label)
        
        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3874BA;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Loading...", self)
        self.status_label.setStyleSheet("color: #333333; font-size: 10pt;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Position layout widget at the bottom of splash screen
        layout.setContentsMargins(20, 10, 20, 20)
        self.layout_widget.setGeometry(0, 200, 500, 100)
    
    def _setup_timer(self):
        """Set up the animation timer"""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_progress)
        # Use a slightly slower update rate
        self.timer.start(60)
    
    def _update_progress(self):
        """Update progress bar and status text"""
        if not hasattr(self, 'progress_bar') or not self.progress_bar:
            # Safety check in case progress bar has been destroyed
            self.timer.stop()
            return
            
        self.counter += 1
        if self.counter <= 100:
            self.progress_bar.setValue(self.counter)
            
            # Update status text
            if self.counter < 20:
                self.status_label.setText("Initializing application...")
            elif self.counter < 40:
                self.status_label.setText("Loading user interface...")
            elif self.counter < 60:
                self.status_label.setText("Preparing robot control modules...")
            elif self.counter < 80:
                self.status_label.setText("Setting up communication systems...")
            else:
                self.status_label.setText("Starting application...")
        else:
            self.timer.stop()
    
    def finish(self, window):
        """Override finish to ensure progress reaches 100% before closing"""
        # Make sure we have valid references before trying to use them
        if not hasattr(self, 'timer') or not self.timer:
            super().finish(window)
            return
        
        # Stop the timer first to prevent any further updates
        if self.timer.isActive():
            self.timer.stop()
        
        try:
            # Complete the progress
            if hasattr(self, 'progress_bar') and self.progress_bar:
                self.progress_bar.setValue(100)
            
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.setText("Ready!")
                
            # Use a safe approach to delay closing
            QTimer.singleShot(300, lambda: self._safe_finish(window))
        except Exception:
            # If any errors occur, just finish normally
            super().finish(window)
    
    def _safe_finish(self, window):
        """Safely call the parent finish method"""
        try:
            super().finish(window)
        except Exception:
            # If an exception occurs during finish, make sure the splash screen is hidden
            self.hide()
            
    def showMessage(self, message, alignment=Qt.AlignLeft, color=Qt.black):
        """Override showMessage to update our custom status label instead"""
        if hasattr(self, 'status_label') and self.status_label:
            self.status_label.setText(message)
        
        # Also call the original implementation for compatibility
        super().showMessage(message, alignment, color) 
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QPlainTextEdit, QLabel, QComboBox, QCheckBox)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QObject, QSize
from PyQt5.QtGui import QFont, QIcon, QTextCursor, QColor, QTextCharFormat, QBrush

class QTextEditLogger(QObject, logging.Handler):
    """
    Custom logging handler that emits log records through a Qt signal
    """
    log_signal = pyqtSignal(str, int)  # Signal to emit log messages and their level
    
    def __init__(self, parent=None):
        super().__init__(parent)
        logging.Handler.__init__(self)
        self.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    def emit(self, record):
        """Emit the log record"""
        msg = self.format(record)
        self.log_signal.emit(msg, record.levelno)


class LogWidget(QWidget):
    """Widget for displaying application logs"""
    
    def __init__(self, logger=None):
        super().__init__()
        
        # Store logger
        self.logger = logger or logging.getLogger()
        
        # Initialize UI
        self.init_ui()
        
        # Set up custom logger handler
        self.setup_logger()
    
    def init_ui(self):
        """Initialize the UI components"""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Controls layout
        controls_layout = QHBoxLayout()
        
        # Clear button
        self.clear_button = QPushButton("Clear Log")
        self.clear_button.setIcon(QIcon("ui/resources/clear.png"))
        self.clear_button.clicked.connect(self.clear_log)
        controls_layout.addWidget(self.clear_button)
        
        # Save button
        self.save_button = QPushButton("Save Log")
        self.save_button.setIcon(QIcon("ui/resources/save.png"))
        self.save_button.clicked.connect(self.save_log)
        controls_layout.addWidget(self.save_button)
        
        # Level filter
        controls_layout.addWidget(QLabel("Level:"))
        self.level_combo = QComboBox()
        self.level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_combo.setCurrentIndex(1)  # INFO by default
        self.level_combo.currentIndexChanged.connect(self.set_log_level)
        controls_layout.addWidget(self.level_combo)
        
        # Auto-scroll checkbox
        self.autoscroll_check = QCheckBox("Auto-scroll")
        self.autoscroll_check.setChecked(True)
        controls_layout.addWidget(self.autoscroll_check)
        
        # Add stretch to push everything to the left
        controls_layout.addStretch(1)
        
        # Add controls layout to main layout
        main_layout.addLayout(controls_layout)
        
        # Log text display
        self.log_display = QPlainTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.log_display.setFont(QFont("Consolas", 9))
        self.log_display.setMaximumBlockCount(5000)  # Limit number of lines to prevent memory issues
        main_layout.addWidget(self.log_display)
    
    def setup_logger(self):
        """Set up custom logger handler"""
        # Create custom handler
        self.log_handler = QTextEditLogger(self)
        self.log_handler.log_signal.connect(self.append_log)
        
        # Set level
        self.set_log_level(self.level_combo.currentIndex())
        
        # Add handler to logger
        self.logger.addHandler(self.log_handler)
    
    @pyqtSlot(str, int)
    def append_log(self, msg: str, level: int):
        """Append log message to the display
        
        Args:
            msg: Log message to append
            level: Logging level (e.g., logging.INFO, logging.ERROR)
        """
        # Format based on level
        text_format = QTextCharFormat()
        
        if level >= logging.CRITICAL:
            text_format.setForeground(QBrush(QColor("darkred")))
            text_format.setFontWeight(QFont.Bold)
        elif level >= logging.ERROR:
            text_format.setForeground(QBrush(QColor("red")))
        elif level >= logging.WARNING:
            text_format.setForeground(QBrush(QColor("orange")))
        elif level >= logging.INFO:
            text_format.setForeground(QBrush(QColor("blue")))
        else:  # DEBUG and below
            text_format.setForeground(QBrush(QColor("green")))
        
        # Store current position
        cursor = self.log_display.textCursor()
        
        # Append text with formatting
        self.log_display.appendPlainText(msg)
        
        # Auto-scroll if enabled
        if self.autoscroll_check.isChecked():
            cursor = self.log_display.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.log_display.setTextCursor(cursor)
    
    def clear_log(self):
        """Clear the log display"""
        self.log_display.clear()
    
    def save_log(self):
        """Save the log to a file"""
        from PyQt5.QtWidgets import QFileDialog
        import time
        
        # Get file name
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Log", f"robot_log_{time.strftime('%Y%m%d_%H%M%S')}.txt", "Text Files (*.txt);;All Files (*)"
        )
        
        if file_name:
            try:
                with open(file_name, 'w') as f:
                    f.write(self.log_display.toPlainText())
                self.logger.info(f"Log saved to {file_name}")
            except Exception as e:
                self.logger.error(f"Error saving log: {str(e)}")
    
    def set_log_level(self, index: int):
        """Set the logging level
        
        Args:
            index: Index from the level combo box
        """
        level_map = {
            0: logging.DEBUG,
            1: logging.INFO,
            2: logging.WARNING,
            3: logging.ERROR,
            4: logging.CRITICAL
        }
        
        level = level_map.get(index, logging.INFO)
        
        # Set handler level
        if hasattr(self, 'log_handler'):
            self.log_handler.setLevel(level)
            
        # Log the level change
        level_name = self.level_combo.currentText()
        self.logger.info(f"Log level changed to {level_name}") 
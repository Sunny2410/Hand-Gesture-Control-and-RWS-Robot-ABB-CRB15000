import cv2
import mediapipe as mp
import os
import sys
import traceback
import time

class HandDetector():
    def __init__(self, min_detection_confidence=0.7):
        """Initialize the hand detector with MediaPipe

        Args:
            min_detection_confidence: Minimum confidence value for hand detection
        """
        self.mpHands = mp.solutions.hands
        self.hands = self.mpHands.Hands(min_detection_confidence=min_detection_confidence)
        self.mpDraw = mp.solutions.drawing_utils
        
        # Thêm các biến cho double tap
        self.tap_count = 0
        self.last_tap_time = 0
        self.triggered = False
        self.tap_timeout = 1.0  # giây

    def findHands(self, img):
        """Detect hands in an image

        Args:
            img: Input image (BGR format from OpenCV)

        Returns:
            Tuple of (processed image with landmarks drawn, hand landmarks list)
        """
        # Convert from BGR to RGB (MediaPipe requires RGB)
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Process with MediaPipe
        results = self.hands.process(imgRGB)
        
        hand_lms = []
        if results.multi_hand_landmarks:
            # Draw landmarks on all detected hands
            for handlm in results.multi_hand_landmarks:
                self.mpDraw.draw_landmarks(img, handlm, self.mpHands.HAND_CONNECTIONS)
                
            # Extract coordinates for the first hand only
            firstHand = results.multi_hand_landmarks[0]
            h, w, _ = img.shape
            for id, lm in enumerate(firstHand.landmark):
                real_x, real_y = int(lm.x * w), int(lm.y * h)
                hand_lms.append([id, real_x, real_y])
                
        return img, hand_lms
    
    def count_finger(self, hand_lms):
        """Count number of extended fingers

        Args:
            hand_lms: Hand landmarks from findHands method

        Returns:
            Number of extended fingers (-1 if no hand detected)
        """
        finger_start_index = [4, 8, 12, 16, 20]  # Index of fingertips
        n_finger = 0
        
        if len(hand_lms) > 0:
            # Check thumb (comparison is different because thumb extends sideways)
            if hand_lms[finger_start_index[0]][1] < hand_lms[finger_start_index[0]-1][1]:
                n_finger += 1
                
            # Check other 4 fingers
            for idx in range(1, 5):
                if hand_lms[finger_start_index[idx]][2] < hand_lms[finger_start_index[idx]-2][2]:
                    n_finger += 1
                    
            return n_finger
        else:
            return -1
            
    def get_option(self, n_fingers):
        """Map finger count to an option number
        
        Args:
            n_fingers: Number of fingers detected
            
        Returns:
            Option number (1-6) or -1 if no hand detected
        """
        if n_fingers == -1:
            return -1
        elif n_fingers == 0:
            return 1  # Option 1
        elif n_fingers == 1:
            return 2  # Option 2
        elif n_fingers == 2:
            return 3  # Option 3
        elif n_fingers == 3:
            return 4  # Option 4
        elif n_fingers == 4:
            return 5  # Option 5
        elif n_fingers >= 5:
            return 6  # Option 6
            
    def get_hand_gesture(self, n_fingers):
        """Get text description of hand gesture
        
        Args:
            n_fingers: Number of fingers detected
            
        Returns:
            Text description of the gesture
        """
        if n_fingers == -1:
            return "Không phát hiện tay"
        elif n_fingers == 0:
            return "Nắm đấm"
        elif n_fingers == 1:
            return "Chỉ tay (1 ngón)"
        elif n_fingers == 2:
            return "Dấu hiệu hòa bình (2 ngón)"
        elif n_fingers == 3:
            return "3 ngón tay"
        elif n_fingers == 4:
            return "4 ngón tay"
        elif n_fingers == 5:
            return "Bàn tay mở (5 ngón)"
        else:
            return f"Cử chỉ không xác định ({n_fingers} ngón)"

    def are_fingers_touching(self, hand_lms, idx1=8, idx2=12, threshold=40):
        """Kiểm tra xem hai ngón tay có chạm nhau không"""
        if len(hand_lms) > max(idx1, idx2):
            x1, y1 = hand_lms[idx1][1], hand_lms[idx1][2]
            x2, y2 = hand_lms[idx2][1], hand_lms[idx2][2]
            dist = ((x2 - x1)**2 + (y2 - y1)**2) ** 0.5
            return dist < threshold
        return False

    def update_double_tap(self, hand_lms, idx1=8, idx2=12):
        """Cập nhật trạng thái double tap, trả về trạng thái trigger/reset
        Đã thêm timeout: chỉ nhận 1 lần tap khi vừa chạm và phải nhả ra mới nhận lần tiếp theo
        """
        fingers_touching = self.are_fingers_touching(hand_lms, idx1, idx2)
        current_time = time.time()
        status = None

        # Thêm biến để nhớ trạng thái lần trước
        if not hasattr(self, '_prev_fingers_touching'):
            self._prev_fingers_touching = False

        # Chỉ tăng tap_count khi vừa chuyển từ không chạm sang chạm
        if fingers_touching and not self._prev_fingers_touching:
            if current_time - self.last_tap_time > 0.5:
                self.tap_count += 1
                self.last_tap_time = current_time

        self._prev_fingers_touching = fingers_touching

        # Reset tap_count nếu quá thời gian
        if self.tap_count == 1 and current_time - self.last_tap_time > self.tap_timeout:
            self.tap_count = 0

        # Trigger khi double tap
        if self.tap_count == 2 and not self.triggered:
            self.triggered = True
            self.tap_count = 0
            status = "triggered"
        elif self.triggered and self.tap_count == 2:
            self.triggered = False
            self.tap_count = 0
            status = "reset"

        return fingers_touching, self.tap_count, status

# Create an alias for backward compatibility
handDetector = HandDetector




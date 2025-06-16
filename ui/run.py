import cv2
import os
import sys

# Ensure the vision module can be imported
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)  # Go up one level to reach the project root
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Import our HandDetector class
from vision.hand_detector import HandDetector

def main():
    # Initialize the hand detector
    detector = HandDetector(min_detection_confidence=0.7)
    
    # Initialize the camera
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        print("Error: Could not open camera")
        return
    
    print("Hand detection running. Press 'q' to quit.")
    
    while True:
        # Read a frame from the camera
        ret, frame = cam.read()
        if not ret:
            print("Error: Could not read frame")
            break
        
        # Flip the frame horizontally for more intuitive display
        frame = cv2.flip(frame, 1)
        
        # Create a rotated version for demonstration
        frame_rotate = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        
        # Process the frame to detect hands
        frame_rotate, hand_lms = detector.findHands(frame_rotate)
        
        # Count fingers and get the corresponding option
        n_fingers = detector.count_finger(hand_lms)
        option = detector.get_option(n_fingers)
        
        # Display the option based on finger count
        if option == 1:
            print("Option 1")
            cv2.putText(frame_rotate, "Option 1", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        elif option == 2:
            print("Option 2")
            cv2.putText(frame_rotate, "Option 2", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        elif option == 3:
            print("Option 3")
            cv2.putText(frame_rotate, "Option 3", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        elif option == 4:
            print("Option 4")
            cv2.putText(frame_rotate, "Option 4", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        elif option == 5:
            print("Option 5")
            cv2.putText(frame_rotate, "Option 5", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        elif option == 6:
            print("Option 6")
            cv2.putText(frame_rotate, "Option 6", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        else:
            print("Không phát hiện tay")
            cv2.putText(frame_rotate, "No hand detected", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        # Show both the original and rotated frames
        cv2.imshow("Rotated View", frame_rotate)
        cv2.imshow("Normal View", frame)
        
        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) == ord("q"):
            break
    
    # Release resources
    cam.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

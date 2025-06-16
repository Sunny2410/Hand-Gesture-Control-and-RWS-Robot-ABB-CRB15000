import cv2
import math
import time
from hand_detector import HandDetector

def are_fingers_touching(hand_lms, idx1=8, idx2=12, threshold=40):
    """
    Kiểm tra xem hai ngón tay có chạm nhau không (theo pixel)
    idx1, idx2: chỉ số landmark của hai đầu ngón
    threshold: ngưỡng khoảng cách pixel để coi là chạm
    """
    if len(hand_lms) > max(idx1, idx2):
        x1, y1 = hand_lms[idx1][1], hand_lms[idx1][2]
        x2, y2 = hand_lms[idx2][1], hand_lms[idx2][2]
        dist = math.hypot(x2 - x1, y2 - y1)
        return dist < threshold
    return False

def is_fist(hand_lms, threshold_ratio=0.3):
    """
    Kiểm tra nếu là nắm đấm dựa trên vị trí tương đối của các đầu ngón tay
    so với lòng bàn tay và mối quan hệ giữa các khớp ngón tay
    """
    if not hand_lms or len(hand_lms) < 21:
        return False
    
    # Lấy tọa độ tâm lòng bàn tay (điểm số 0, 5, 9, 13, 17)
    palm_x = (hand_lms[0][1] + hand_lms[5][1] + hand_lms[9][1] + hand_lms[13][1] + hand_lms[17][1]) / 5
    palm_y = (hand_lms[0][2] + hand_lms[5][2] + hand_lms[9][2] + hand_lms[13][2] + hand_lms[17][2]) / 5
    
    # Tính khoảng cách từ cổ tay đến tâm lòng bàn tay để làm ngưỡng tham chiếu
    wrist_to_palm = math.hypot(palm_x - hand_lms[0][1], palm_y - hand_lms[0][2])
    threshold = wrist_to_palm * threshold_ratio
    
    # Các điểm mút của ngón tay (ngón cái, trỏ, giữa, áp út, út)
    finger_tips = [4, 8, 12, 16, 20]
    # Các điểm gốc ngón tay (điểm nối với lòng bàn tay)
    finger_bases = [1, 5, 9, 13, 17]
    # Các khớp thứ hai của ngón tay
    finger_mids = [3, 7, 11, 15, 19]
    
    # Đếm số ngón tay đang co (đầu ngón gần lòng bàn tay)
    bent_fingers = 0
    
    for i in range(5):  # Kiểm tra từng ngón tay
        tip_idx = finger_tips[i]
        base_idx = finger_bases[i]
        mid_idx = finger_mids[i]
        
        # Tính khoảng cách từ đầu ngón đến tâm lòng bàn tay
        tip_to_palm = math.hypot(hand_lms[tip_idx][1] - palm_x, hand_lms[tip_idx][2] - palm_y)
        
        # Tính khoảng cách từ gốc ngón đến tâm lòng bàn tay
        base_to_palm = math.hypot(hand_lms[base_idx][1] - palm_x, hand_lms[base_idx][2] - palm_y)
        
        # Đối với ngón cái, xử lý đặc biệt
        if i == 0:  # Ngón cái
            # Kiểm tra ngón cái có đang co vào hay không
            if tip_to_palm < base_to_palm * 1.5:
                bent_fingers += 1
        else:
            # Kiểm tra các ngón khác: Đầu ngón phải gần lòng bàn tay hơn khớp giữa
            mid_to_palm = math.hypot(hand_lms[mid_idx][1] - palm_x, hand_lms[mid_idx][2] - palm_y)
            if tip_to_palm < mid_to_palm:
                bent_fingers += 1
    
    # Được coi là nắm đấm nếu ít nhất 4 ngón tay đều co
    return bent_fingers >= 4

def run_hand_detector():
    cap = cv2.VideoCapture(0)
    detector = HandDetector()

    tap_count = 0
    last_tap_time = 0
    triggered = False
    tap_timeout = 1.0  # giây, khoảng thời gian tối đa giữa 2 lần chập để tính là double tap
    
    # Thêm đếm thời gian để ổn định nhận diện nắm đấm
    fist_counter = 0
    fist_detected = False
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        img, hand_lms = detector.findHands(frame)
        
        # Kiểm tra nắm đấm trước khi đếm ngón tay 
        if is_fist(hand_lms):
            fist_counter += 1
            if fist_counter > 3:  # Cần phát hiện nắm đấm liên tục vài frame để xác nhận
                fist_detected = True
        else:
            fist_counter = max(0, fist_counter - 1)
            if fist_counter == 0:
                fist_detected = False
        
        if fist_detected:
            gesture = "Nắm đấm"
            n_fingers = 0
        else:
            n_fingers = detector.count_finger(hand_lms)
            gesture = detector.get_hand_gesture(n_fingers)
            
            fingers_touching = are_fingers_touching(hand_lms, 4, 8)

            # Double tap detection
            current_time = time.time()
            if fingers_touching:
                if current_time - last_tap_time > 0.5:  # tránh đếm liên tục khi giữ chập
                    tap_count += 1
                    last_tap_time = current_time

            # Reset tap_count nếu quá thời gian
            if tap_count == 1 and current_time - last_tap_time > tap_timeout:
                tap_count = 0

            # Trigger khi double tap
            if tap_count == 2 and not triggered:
                gesture += " + Đã kích hoạt!"
                print("Đã kích hoạt!")
                triggered = True
                tap_count = 0  # reset để chờ lần double tap tiếp theo

            # Reset trigger nếu double tap lần nữa
            if triggered and tap_count == 2:
                gesture += " + Đã reset!"
                print("Đã reset!")
                triggered = False
                tap_count = 0

            if fingers_touching:
                gesture += " + Chập 2 ngón!"

        # Hiển thị thông tin debug
        cv2.putText(img, f'Fingers: {n_fingers}', (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
        cv2.putText(img, gesture, (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2)
        cv2.putText(img, f'Tap Count: {tap_count}', (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
        cv2.putText(img, f'Fist Counter: {fist_counter}', (10, 160), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,255), 2)
        
        cv2.imshow("Hand Detector", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_hand_detector()
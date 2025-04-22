import cv2

cap = cv2.VideoCapture("http://192.168.31.116:5000/video")

while True:
    ret, frame = cap.read()
    if not ret:
        break
    cv2.imshow("Stream", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

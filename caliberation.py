# calibrate.py

import cv2
from ultralytics import YOLO
import json

def calibrate(model_path="models/model.pt", output_file="calibration.json"):
    model = YOLO(model_path)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    distances = []
    areas = []

    print("Calibration mode:")
    print(" - Place your subject at a known distance (cm).")
    print(" - Press 'c' to capture the bounding‑box area at that distance.")
    print(" - Press 'q' to finish and compute calibration constant.\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame, conf=0.4, verbose=False)
        annotated = frame.copy()

        if results[0].boxes:
            box = results[0].boxes[0]
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)

        cv2.imshow("Calibration", annotated)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('c') and results[0].boxes:
            d = float(input("Enter known distance in cm: "))
            area_px = (x2 - x1) * (y2 - y1)
            distances.append(d)
            areas.append(area_px)
            print(f"Captured area={area_px} px² at {d} cm\n")

        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    # Compute K = A * d^2 for each sample, then average
    Ks = [areas[i] * distances[i]**2 for i in range(len(distances))]
    K = sum(Ks) / len(Ks)

    with open(output_file, "w") as f:
        json.dump({"K": K}, f)

    print(f"\nCalibration complete. K = {K:.2f} saved to {output_file}")

if __name__ == "__main__":
    calibrate()

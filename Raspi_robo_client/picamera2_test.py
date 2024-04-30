import cv2
from picamera2.picamera2 import Picamera2

# Initialize picamera2
picamera2 = Picamera2()
preview_config = picamera2.create_preview_configuration()
picamera2.configure(preview_config)
picamera2.start()

try:
    while True:
        # Capture a frame
        frame = picamera2.capture_array()
        # Convert to a format OpenCV can use
        image = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        # Display the image
        cv2.imshow("Video Feed", image)
        
        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    # Cleanup
    cv2.destroyAllWindows()
    picamera2.stop()
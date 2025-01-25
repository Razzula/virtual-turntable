import cv2
from pyzbar.pyzbar import decode
import matplotlib.pyplot as plt

camera = cv2.VideoCapture(0)

frameWidth = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
frameHeight = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))

# fourcc = cv2.VideoWriter_fourcc(*'mp4v')
# out = cv2.VideoWriter('output.mp4', fourcc, 20.0, (frameWidth, frameHeight))

# while (True):
#     ret, frame = camera.read()

#     if (not ret):
#         break

#     grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#     # (thresh, mono) = cv2.threshold(grey, 127, 255, cv2.THRESH_BINARY)
#     barcodes = decode(grey)

#     for barcode in barcodes:
#         print(':D')

#     # out.write(gray) # write to video file
#     cv2.imshow('frame', grey) # display video

#     if (cv2.waitKey(1) & 0xFF == ord('q')):
#         break

image = cv2.imread("barcode3.jpg")

grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
barcodes = decode(grey)
for barcode in barcodes:
    barcode_data = barcode.data.decode("utf-8")
    barcode_type = barcode.type

    # Print barcode data and type
    print("Barcode Data:", barcode_data)
    print("Barcode Type:", barcode_type)

    (x, y, w, h) = barcode.rect
    cv2.rectangle(image, (x, y), (x + w, y + h), (255, 0, 0), 2)

    cv2.putText(image, f"{barcode_data} ({barcode_type})",
                (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

imageRGB = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

plt.imshow(imageRGB)
plt.axis('off')
plt.show()

camera.release()
# out.release()
cv2.destroyAllWindows()

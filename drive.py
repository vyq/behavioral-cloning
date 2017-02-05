from flask import Flask, render_template
from io import BytesIO
from keras.models import model_from_json
from keras.preprocessing.image import ImageDataGenerator, array_to_img, img_to_array
from PIL import Image
from PIL import ImageOps
import argparse
import base64
import cv2
import eventlet
import eventlet.wsgi
import json
import numpy as np
import socketio
import time

# Fix error with Keras and TensorFlow
import tensorflow as tf
tf.python.control_flow_ops = tf

sio = socketio.Server()
app = Flask(__name__)
model = None
prev_image_array = None

@sio.on('telemetry')
def telemetry(sid, data):
    steering_angle = data["steering_angle"]
    throttle = data["throttle"]
    speed = data["speed"]
    # The current image from the center camera of the car
    imgString = data["image"]
    image = Image.open(BytesIO(base64.b64decode(imgString)))
    image_array = np.asarray(image)
    y_start = 64
    y_end = image_array.shape[0] - 30
    x_start = 60
    x_end = image_array.shape[1] - 60
    image_array = image_array[y_start:y_end, x_start:x_end]
    image_array = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
    image_array = image_array / 255
    transformed_image_array = image_array.reshape(
        1,
        image_array.shape[0],
        image_array.shape[1],
        1
    )
    steering_angle = float(
        model.predict(
            transformed_image_array,
            batch_size=1
        )
    )
    if (float(speed) > 10.0):
        throttle = 0.0
    else:
        throttle = 0.2
    print(steering_angle, throttle)
    send_control(steering_angle, throttle)

@sio.on('connect')
def connect(sid, environ):
    print("connect ", sid)
    send_control(0, 0)

def send_control(steering_angle, throttle):
    sio.emit("steer", data={
    'steering_angle': steering_angle.__str__(),
    'throttle': throttle.__str__()
    }, skip_sid=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'Remote Driving')
    parser.add_argument(
        'model',
        type = str,
        help = 'Path to model definition json. Model weights should be on the same path.'
    )
    args = parser.parse_args()
    with open(args.model, 'r') as jfile:
        model = model_from_json(jfile.read())

    model.compile("adam", "mse")
    weights_file = args.model.replace('json', 'h5')
    model.load_weights(weights_file)

    # Wrap Flask application with engineio's middleware
    app = socketio.Middleware(sio, app)

    # Deploy as an eventlet WSGI server
    eventlet.wsgi.server(eventlet.listen(('', 4567)), app)
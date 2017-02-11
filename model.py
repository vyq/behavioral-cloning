# Import libraries
from keras.layers.convolutional import Convolution2D, Cropping2D
from keras.layers.core import Dense, Flatten, Lambda
from keras.models import model_from_json, Sequential
from keras.optimizers import Adam
from matplotlib import pyplot
from sklearn.model_selection import train_test_split
from sklearn.utils import shuffle
import csv
import cv2
import fnmatch
import math
import numpy as np
import os
import scipy

# Set parameters
PATH = './data'
DRIVING_LOG_FILE = 'driving_log.csv'
BATCH_SIZE = 32

IMAGE_WIDTH = 160
IMAGE_LENGTH = 320
IMAGE_DEPTH = 1

STEERING_ANGLE_MODIFIER = 0.2

CROP_TOP = 64
CROP_BOTTOM = 30

LEARNING_RATE = 0.000001

SAMPLES_PER_EPOCH = 12#19284
EPOCH = 2
VERBOSITY = 2
VALIDATION_SET_SIZE = 3#4821

# Get data
samples = []
with open(os.path.join(PATH, DRIVING_LOG_FILE), 'r') as file:
    reader = csv.reader(file)
    reader.__next__()
    for line in reader:
        samples.append(line)

training_set, validation_set = train_test_split(samples, test_size = 0.2)

def generate_sample(reader, samples, batch_size = BATCH_SIZE):
    sample_count = len(samples)

    while True:
        shuffle(samples)

        for offset in range(0, sample_count, batch_size):
            batch_samples = samples[offset : offset + batch_size]

            images = []
            angles = []

            for batch_sample in batch_samples:
                path = os.path.join(PATH, batch_sample[0].strip())
                center_image = cv2.imread(path)
                center_image = transform_image(center_image)
                center_angle = np.array(
                    batch_sample[3],
                    dtype = 'float32'
                )
                center_angle = transform_steering_angle(center_angle)
                images.extend(center_image)
                angles.extend(center_angle)

            print(np.array(images).shape, np.array(angles).shape)
            exit()

        line = reader.__next__()
        
        path = os.path.join(PATH, line[0].strip())
        center_image = cv2.imread(path)
        flipped_center_image = cv2.flip(center_image, 1)
        center_image = transform_image(center_image)
        flipped_center_image = transform_image(flipped_center_image)
        path = os.path.join(PATH, line[1].strip())
        left_image = cv2.imread(path)
        flipped_left_image = cv2.flip(left_image, 1)
        left_image = transform_image(left_image)
        flipped_left_image = transform_image(flipped_left_image)
        path = os.path.join(PATH, line[2].strip())
        right_image = cv2.imread(path)
        flipped_right_image = cv2.flip(right_image, 1)
        right_image = transform_image(right_image)
        flipped_right_image = transform_image(flipped_right_image)
        image = np.concatenate((
            center_image,
            flipped_center_image,
            left_image,
            flipped_left_image,
            right_image,
            flipped_right_image
        ))

        center_steering_angle = np.array(line[3], dtype = 'float32')
        center_steering_angle = transform_steering_angle(
            center_steering_angle
        )
        flipped_center_steering_angle = transform_steering_angle(
            center_steering_angle[0][0] * -1.0
        )
        left_steering_angle = transform_steering_angle(
            center_steering_angle,
            STEERING_ANGLE_MODIFIER
        )
        flipped_left_steering_angle = transform_steering_angle(
            left_steering_angle[0][0] * -1.0
        )
        right_steering_angle = transform_steering_angle(
            center_steering_angle,
            -STEERING_ANGLE_MODIFIER
        )
        flipped_right_steering_angle = transform_steering_angle(
            right_steering_angle[0][0] * -1.0
        )
        steering_angle = np.concatenate((
            center_steering_angle,
            flipped_center_steering_angle,
            left_steering_angle,
            flipped_left_steering_angle,
            right_steering_angle,
            flipped_right_steering_angle
        ))

        yield (image, steering_angle)

def generate_training_sample():
    file = open(os.path.join(PATH, DRIVING_LOG_FILE), 'r')
    reader = csv.reader(file)
    reader.__next__()
    yield from generate_sample(reader, samples)
    file.close()

def generate_validation_sample():
    file = open(os.path.join(PATH, DRIVING_LOG_FILE), 'r')
    reader = csv.reader(file)
    reader = reversed(list(reader))
    yield from generate_sample(reader, samples)
    file.close()

# Transform data
def transform_image(image):
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    image = np.array(image, dtype = 'float32')

    return image.reshape(
        1,
        IMAGE_WIDTH,
        IMAGE_LENGTH,
        IMAGE_DEPTH
    )

def transform_steering_angle(steering_angle, modifier = 0.0):
    steering_angle = steering_angle + modifier
    return steering_angle.reshape(1, 1)

# Design model
convolution_filter = 24
kernel_size = 5
stride_size = 2
model = Sequential()
model.add(
    Cropping2D(
        cropping = ((CROP_TOP, CROP_BOTTOM), (0, 0)),
        input_shape = (IMAGE_WIDTH, IMAGE_LENGTH, IMAGE_DEPTH)
    )
)
model.add(Lambda(lambda x: x / 255.0 - 0.5))
model.add(Convolution2D(
    convolution_filter,
    kernel_size,
    kernel_size,
    border_mode = 'valid',
    subsample = (stride_size, stride_size)
))
convolution_filter = 36
model.add(Convolution2D(
    convolution_filter,
    kernel_size,
    kernel_size,
    border_mode = 'valid',
    subsample = (stride_size, stride_size)
))
convolution_filter = 48
model.add(Convolution2D(
    convolution_filter,
    kernel_size,
    kernel_size,
    border_mode = 'valid',
    subsample = (stride_size, stride_size)
))
convolution_filter = 64
kernel_size = 3
model.add(Convolution2D(
    convolution_filter,
    kernel_size,
    kernel_size,
    border_mode = 'valid'
))
model.add(Convolution2D(
    convolution_filter,
    kernel_size,
    kernel_size,
    border_mode = 'valid'
))
model.add(Flatten())
model.add(Dense(100))
model.add(Dense(50))
model.add(Dense(10))
model.add(Dense(1))

# Train model
adam = Adam(lr = LEARNING_RATE)
model.compile(optimizer = adam, loss = 'mse')
history = model.fit_generator(
    generate_training_sample(),
    samples_per_epoch = SAMPLES_PER_EPOCH,
    nb_epoch = EPOCH,
    verbose = VERBOSITY,
    validation_data = generate_validation_sample(),
    nb_val_samples = VALIDATION_SET_SIZE
)

# Save model
model_json = model.to_json()
json_file = open('model.json', 'w')
json_file.write(model_json)
model.save_weights('model.h5')

# Save chart
chart = pyplot.gcf()
pyplot.plot(history.history['loss'])
pyplot.plot(history.history['val_loss'])
pyplot.legend(['Training', 'Validation'])
pyplot.ylabel('Loss')
pyplot.xlabel('Epoch')
chart.savefig('loss.png')
import argparse

import numpy as np
import cv2 as cv

from mp_palmdet import MPPalmDet

def str2bool(v):
    if v.lower() in ['on', 'yes', 'true', 'y', 't']:
        return True
    elif v.lower() in ['off', 'no', 'false', 'n', 'f']:
        return False
    else:
        raise NotImplementedError

backends = [cv.dnn.DNN_BACKEND_OPENCV, cv.dnn.DNN_BACKEND_CUDA]
targets = [cv.dnn.DNN_TARGET_CPU, cv.dnn.DNN_TARGET_CUDA, cv.dnn.DNN_TARGET_CUDA_FP16]
help_msg_backends = "Choose one of the computation backends: {:d}: OpenCV implementation (default); {:d}: CUDA"
help_msg_targets = "Chose one of the target computation devices: {:d}: CPU (default); {:d}: CUDA; {:d}: CUDA fp16"
try:
    backends += [cv.dnn.DNN_BACKEND_TIMVX]
    targets += [cv.dnn.DNN_TARGET_NPU]
    help_msg_backends += "; {:d}: TIMVX"
    help_msg_targets += "; {:d}: NPU"
except:
    print('This version of OpenCV does not support TIM-VX and NPU. Visit https://github.com/opencv/opencv/wiki/TIM-VX-Backend-For-Running-OpenCV-On-NPU for more information.')

parser = argparse.ArgumentParser(description='Hand Detector from MediaPipe')
parser.add_argument('--input', '-i', type=str, help='Usage: Set path to the input image. Omit for using default camera.')
parser.add_argument('--model', '-m', type=str, default='./palm_detection_mediapipe_2022may.onnx', help='Usage: Set model path, defaults to palm_detection_mediapipe_2022may.onnx.')
parser.add_argument('--backend', '-b', type=int, default=backends[0], help=help_msg_backends.format(*backends))
parser.add_argument('--target', '-t', type=int, default=targets[0], help=help_msg_targets.format(*targets))
parser.add_argument('--score_threshold', type=float, default=0.99, help='Usage: Set the minimum needed confidence for the model to identify a palm, defaults to 0.99. Smaller values may result in faster detection, but will limit accuracy. Filter out faces of confidence < conf_threshold. An empirical score threshold for the quantized model is 0.49.')
parser.add_argument('--nms_threshold', type=float, default=0.3, help='Usage: Suppress bounding boxes of iou >= nms_threshold. Default = 0.3.')
parser.add_argument('--save', '-s', type=str, default=False, help='Usage: Set “True” to save file with results (i.e. bounding box, confidence level). Invalid in case of camera input. Default will be set to “False”.')
parser.add_argument('--vis', '-v', type=str2bool, default=True, help='Usage: Default will be set to “True” and will open a new window to show results. Set to “False” to stop visualizations from being shown. Invalid in case of camera input.')
args = parser.parse_args()

def visualize(image, results, print_results=False, fps=None):
    output = image.copy()

    if fps is not None:
        cv.putText(output, 'FPS: {:.2f}'.format(fps), (0, 15), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255))

    for idx, palm in enumerate(results):
        score = palm[-1]
        palm_box = palm[0:4]
        palm_landmarks = palm[4:-1].reshape(7, 2)

        # put score
        palm_box = palm_box.astype(np.int32)
        cv.putText(output, '{:.4f}'.format(score), (palm_box[0], palm_box[1]+12), cv.FONT_HERSHEY_DUPLEX, 0.5, (0, 255, 0))

        # draw box
        cv.rectangle(output, (palm_box[0], palm_box[1]), (palm_box[2], palm_box[3]), (0, 255, 0), 2)

        # draw points
        palm_landmarks = palm_landmarks.astype(np.int32)
        for p in palm_landmarks:
            cv.circle(output, p, 2, (0, 0, 255), 2)

        # Print results
        if print_results:
            print('-----------palm {}-----------'.format(idx + 1))
            print('score: {:.2f}'.format(score))
            print('palm box: {}'.format(palm_box))
            print('palm landmarks: ')
            for plm in palm_landmarks:
                print('\t{}'.format(plm))

    return output

if __name__ == '__main__':
    # Instantiate MPPalmDet
    model = MPPalmDet(modelPath=args.model,
                      nmsThreshold=args.nms_threshold,
                      scoreThreshold=args.score_threshold,
                      backendId=args.backend,
                      targetId=args.target)

    # If input is an image
    if args.input is not None:
        image = cv.imread(args.input)

        # Inference
        results = model.infer(image)
        if len(results) == 0:
            print('Hand not detected')

        # Draw results on the input image
        image = visualize(image, results, print_results=True)

        # Save results if save is true
        if args.save:
            print('Resutls saved to result.jpg\n')
            cv.imwrite('result.jpg', image)

        # Visualize results in a new window
        if args.vis:
            cv.namedWindow(args.input, cv.WINDOW_AUTOSIZE)
            cv.imshow(args.input, image)
            cv.waitKey(0)
    else: # Omit input to call default camera
        deviceId = 0
        cap = cv.VideoCapture(deviceId)

        tm = cv.TickMeter()
        while cv.waitKey(1) < 0:
            hasFrame, frame = cap.read()
            if not hasFrame:
                print('No frames grabbed!')
                break

            # Inference
            tm.start()
            results = model.infer(frame)
            tm.stop()

            # Draw results on the input image
            frame = visualize(frame, results, fps=tm.getFPS())

            # Visualize results in a new Window
            cv.imshow('MPPalmDet Demo', frame)

            tm.reset()


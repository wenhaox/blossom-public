from tracemalloc import stop
from deepface.commons import functions
from enum import Enum
import math
import numpy as np
from numpy.random import default_rng
import random
from pypot.creatures import PoppyErgoJr
from pypot.primitive.primitive import LoopPrimitive
import time

import cv2

class Poppy:
    def __init__(self) -> None:
        self.state = self.State.IDLE
        self.robot = PoppyErgoJr(camera='dummy')
        self._base = [30, -30, -25, 0, 18, 13]
        self._watch_screen = [-50, -35, -23, -15, 11, 18]
        self._sleep = [0, -90, 75, 0, 25, 45]
        self._move_breathe = self.MoveBreathe(self.robot, 2.0)
        self._move_normal = self.MoveNormal(self.robot, 4.0)
        self._move_excited = self.MoveExcited(self.robot, 8.0)
        self._face_tracking = self.FaceTracking(self.robot, 30.0)
        # all backend options: 'opencv', 'ssd', 'dlib', 'mtcnn', 'retinaface', 'mediapipe'
        # self._face_tracking = self.FaceTracking(self.robot, 30.0, 'opencv')
        for m in self.robot.motors:
            m.compliant = False

    def base_pose(self):
        self.stop()
        for i in range(6):
            self.robot.motors[i].moving_speed = 30
            self.robot.motors[i].goal_position = self._base[i]

    def watch_screen(self):
        self.stop()
        for i in range(6):
            self.robot.motors[i].moving_speed = 40
            self.robot.motors[i].goal_position = self._watch_screen[i]

    # def watch_button(self):
    #     self.stop()
    #     for m in self.robot.motors:
    #         m.moving_speed = 40
    #     self.robot.m1.goal_position = -30
    #     self.robot.m2.goal_position = -16
    #     self.robot.m3.goal_position = -20
    #     self.robot.m4.goal_position = 0
    #     self.robot.m5.goal_position = 20
    #     self.robot.m6.goal_position = 32
        
    def sleep(self):
        self.stop()
        for i in range(6):
            self.robot.motors[i].moving_speed = 5
            self.robot.motors[i].goal_position = self._sleep[i]

    def face_tracking(self, short=False):
        self.stop()
        if short:
            self._face_tracking.run_short()
        else:
            self._face_tracking.start()
            self.state = self.State.TRACKING

    def move_breathe(self):
        self.stop()
        self._move_breathe.start()
        self.state = self.State.BREATHE

    def move_normal(self):
        self.stop()
        self._move_normal.start()
        self.state = self.State.NORMAL

    def move_excited(self):
        self.stop()
        self._move_excited.start()
        self.state = self.State.EXCITED
        
    def stop(self):
        if self.state == self.State.BREATHE:
            self._move_breathe.stop()
        elif self.state == self.State.NORMAL:
            self._move_normal.stop()
        elif self.state == self.State.EXCITED:
            self._move_excited.stop()
        elif self.state == self.State.TRACKING:
            self._face_tracking.stop()
        self.state = self.State.IDLE
        for m in self.robot.motors:
            m.led = 'off'


    class State(Enum):
        IDLE = 1
        BREATHE = 2
        NORMAL = 3
        EXCITED = 4
        TRACKING = 5


    class MoveBreathe(LoopPrimitive):
        def __init__(self, robot, freq):
            super().__init__(robot, freq)
            self.up = [30, -30, -25, 0, 18, 13]
            self.down = [30, -30, -25, 0, 33, 30]
            self.curious = [30, -90, 45, 0, 45, 0]
            self.stretch = [30, -15, -45, 0, -5, 35]
            self.sleep = [0, -90, 75, 0, 25, 45]

        def setup(self):
            self.rng = default_rng()
            self.go_up = False
            self.state = self.State.BREATHE
            self.count = 5
            self.start_time = time.perf_counter()
            for m in self.robot.motors:
                m.led = 'cyan'

        def update(self):
            if self.count == 5:
                self.count = 0
                if self.state == self.State.BREATHE:
                    for m in self.robot.motors:
                        m.moving_speed = 10
                    if self.go_up:
                        for i in range(6):
                            self.robot.motors[i].goal_position = self.up[i]
                    else:
                        for i in range(6):
                            self.robot.motors[i].goal_position = self.down[i]
                    if time.perf_counter() - self.start_time > 60*30: # goes to sleep after 30 minutes
                        for m in self.robot.motors:
                            m.moving_speed = 5
                        for i in range(6):
                            self.robot.motors[i].moving_speed = 5
                            self.robot.motors[i].goal_position = self.sleep[i]
                        self.stop()
                    elif time.perf_counter() - self.start_time > 60*10: # only execute after ten minutes of starting
                        rand_switch = self.rng.integers(low=0,high=2400)
                        if (rand_switch < 10): # this is around once every ten minutes
                            if self.go_up:
                                self.state = self.State.CURIOUS_1
                            else:
                                self.state = self.State.STRETCH_1
                    self.go_up = not self.go_up
                elif self.state == self.State.CURIOUS_1:
                    rand_1 = self.rng.integers(low=20,high=60,endpoint=True)
                    if rand_1 % 2 == 0:
                        rand_1 = -rand_1
                    rand_4 = self.rng.integers(low=-50,high=50,endpoint=True)
                    rand = [rand_1, 0, 0, rand_4, 0, 0]
                    led = ['cyan', 'off', 'cyan', 'off', 'cyan', 'off']
                    for i in range(6):
                        self.robot.motors[i].moving_speed = 45
                        self.robot.motors[i].goal_position = self.curious[i] + rand[i]
                        self.robot.motors[i].led = led[i]
                    self.state = self.State.CURIOUS_2
                elif self.state == self.State.CURIOUS_2:
                    rand_1 = self.rng.integers(low=20,high=60,endpoint=True)
                    if rand_1 % 2 == 0:
                        rand_1 = -rand_1                
                    rand_4 = self.rng.integers(low=-50,high=50,endpoint=True)
                    rand = [rand_1, 0, 0, rand_4, 0, 0]
                    led = ['off', 'cyan', 'off', 'cyan', 'off', 'cyan']
                    for i in range(6):
                        self.robot.motors[i].goal_position = self.curious[i] + rand[i]
                        self.robot.motors[i].led = led[i]
                    self.state = self.State.CURIOUS_3
                elif self.state == self.State.CURIOUS_3:
                    for i in range(6):
                        self.robot.motors[i].goal_position = self.up[i]
                    self.go_up = False
                    for m in self.robot.motors:
                        m.led = 'cyan'
                    self.state = self.State.BREATHE
                elif self.state == self.State.STRETCH_1:
                    rand_1 = self.rng.integers(low=-20,high=20,endpoint=True)
                    rand_4 = self.rng.integers(low=-10,high=10,endpoint=True)
                    rand_6 = self.rng.integers(low=-15,high=15,endpoint=True)
                    rand = [rand_1, 0, 0, rand_4, 0, rand_6]
                    led = ['cyan', 'off', 'cyan', 'off', 'cyan', 'off']
                    for i in range(6):
                        self.robot.motors[i].moving_speed = 45
                        self.robot.motors[i].goal_position = self.stretch[i] + rand[i]
                        self.robot.motors[i].led = led[i]
                    self.state = self.State.STRETCH_2
                elif self.state == self.State.STRETCH_2:
                    for i in range(6):
                        self.robot.motors[i].led = 'cyan'
                        self.robot.motors[i].goal_position = self.down[i]
                    self.go_up = True
                    self.state = self.State.BREATHE
            self.count += 1

        def teardown(self):
            for i in range(6):
                self.robot.motors[i].led = 'off'


        class State(Enum):
            BREATHE = 1
            CURIOUS_1 = 2
            CURIOUS_2 = 3
            CURIOUS_3 = 4
            STRETCH_1 = 5
            STRETCH_2 = 6

    
    class MoveNormal(LoopPrimitive):
        def __init__(self, robot, freq):
            super().__init__(robot, freq)
            self.rng = default_rng()
            self.colors = ['yellow', 'pink', 'white']
            self.move_sets = [[1,2], [1,4], [1,5], [2,4], [2,5], [4,5], [1,2,4], [1,2,5], [2,4,5], [1,2,4,5]]

        def move(self, center):
            self.center = center
            self.start()

        def setup(self):
            self.on_led = 0
            self.count = 1
            self.center = []
            for m in self.robot.motors:
                m.moving_speed = 50
                self.center.append(m.goal_position)

        def update(self):
            if self.count == 1:
                selected_motors = random.choice(self.move_sets)
                self.random_motion = np.zeros((6,),dtype=int)
                for i in selected_motors:
                    if i == np.amax(selected_motors):
                        self.random_motion[i] = -np.sum(self.random_motion)
                    elif i < 3:
                        self.random_motion[i] = self.rng.integers(low=-15,high=15,endpoint=True)
                    elif i > 3:
                        self.random_motion[i] = self.rng.integers(low=-25,high=25,endpoint=True)
                    self.random_motion[3] = self.rng.integers(low=-5,high=5,endpoint=True)
            elif self.count == 2:
                self.count = 0
                for i in range(6):
                    self.robot.motors[i].goal_position = self.center[i] + self.random_motion[i]
            self.count += 1
            for i in range(6):
                if i == self.on_led or i == (self.on_led+1)%6:
                    self.robot.motors[i].led = random.choice(self.colors)
                else:
                    self.robot.motors[i].led = 'off'
            self.on_led = (self.on_led+1)%6

        def teardown(self):
            self.center = [30, -30, -25, 0, 18, 13]
            for i in range(6):
                self.robot.motors[i].led = 'off'
                self.robot.motors[i].goal_position = self.center[i]
                
    

    class MoveExcited(LoopPrimitive):
        def __init__(self, robot, freq):
            super().__init__(robot, freq)
            self.rng = default_rng()
            self.colors = ['red', 'blue']
            self.move_sets = [[1,2], [1,4], [1,5], [2,4], [2,5], [4,5], [1,2,4], [1,2,5], [2,4,5], [1,2,4,5]]

        def move(self, center):
            self.center = center
            self.start()

        def setup(self):
            self.on_led = 0
            self.count = 1
            self.center = []
            for m in self.robot.motors:
                m.moving_speed = 60
                self.center.append(m.goal_position)

        def update(self):
            if self.count == 1:
                selected_motors = random.choice(self.move_sets)
                self.random_motion = np.zeros((6,),dtype=int)
                for i in selected_motors:
                    if i == np.amax(selected_motors):
                        self.random_motion[i] = -np.sum(self.random_motion)
                    elif i < 3:
                        self.random_motion[i] = self.rng.integers(low=-15,high=15,endpoint=True)
                    elif i > 3:
                        self.random_motion[i] = self.rng.integers(low=-25,high=25,endpoint=True)
                self.random_motion[3] = self.rng.integers(low=-10,high=10,endpoint=True)
            elif self.count == 2:
                self.count = 0
                for i in range(6):
                    self.robot.motors[i].goal_position = self.center[i] + self.random_motion[i]
            self.count += 1
            for i in range(6):
                if i == self.on_led or i == (self.on_led+1)%6:
                    self.robot.motors[i].led = random.choice(self.colors)
                else:
                    self.robot.motors[i].led = 'off'
            self.on_led = (self.on_led+1)%6

        def teardown(self):
            self.center = [30, -30, -25, 0, 18, 13]
            for i in range(6):
                self.robot.motors[i].led = 'off'
                self.robot.motors[i].goal_position = self.center[i]


    class FaceTracking(LoopPrimitive):
        def __init__(self, robot, freq):
            super().__init__(robot, freq)
            self.rest = [30, -30, -25, 0, 18, 13]
            self.detector = cv2.CascadeClassifier('Cascades/haarcascade_frontalface_default.xml')
            self.img_size = [640, 480]
            self.short = False

        # Uncomment this constructor for original algorithm
        # def __init__(self, robot, freq, face_detector):
        #     super().__init__(robot, freq)
        #     self.rest = [30, -60, 20, 0, 20, 17]
        #     for m in self.robot.motors:
        #         m.moving_speed = 120
        #         m.led = 'green'
        #     self.detector = face_detector
        #     self.cap = cv2.VideoCapture(0)
        #     success = False
        #     while not success:
        #         success, image = self.cap.read()
        #     self.img_size = tuple(reversed(image.shape[:2]))
        #     self.cap.release()

        def run_short(self):
            self.short = True
            self.count = 0
            self.start()

        def setup(self):
            self.robot.m1.goal_position = self.rest[0]
            self.robot.m2.goal_position = self.rest[1]
            self.robot.m3.goal_position = self.rest[2]
            self.robot.m4.goal_position = self.rest[3]
            self.robot.m5.goal_position = self.rest[4]
            self.robot.m6.goal_position = self.rest[5]
            for m in self.robot.motors:
                m.moving_speed = 60
                m.led = 'green'
            self.cap = cv2.VideoCapture(0)
            if self.cap.isOpened():
                # the two following lines are for the new algorithm
                self.cap.set(3, self.img_size[0]) # set width
                self.cap.set(4, self.img_size[1]) # set height
            else:
                self.stop()

        def update(self):
            if self.cap.isOpened():
                success, image = self.cap.read()
                if not success:
                    return
                # following two lines are for new algorithm
                image = cv2.flip(image, 0) #-1
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                # To improve performance, optionally mark the image as not writeable to pass by reference.
                image.flags.writeable = False
                # this line below and the conditional are also for new algorithm
                faces = self.detector.detectMultiScale(
                            gray,
                            
                            scaleFactor=1.2,
                            minNeighbors=5
                            ,     
                            minSize=(20, 20)
                        )
                if len(faces) != 0:
                    region = faces[0]
                # Uncomment the following two lines for original algorithm
                # face_img, region = functions.preprocess_face(image, detector_backend=self.detector, enforce_detection=False, return_region=True)
                # if region[0] != 0 and region[1] != 0:
                    x = region[0]+0.5*region[2]
                    y = region[1]+0.5*region[3]
                    cam_z = 200*pow(region[2]*region[3],-0.6)
                    img_x = cam_z/1.4*1.8
                    img_y = cam_z/1.4*1.2
                    cam_x = ((float(x) / self.img_size[0]) - 0.5) * img_x
                    cam_y = ((float(y) / self.img_size[1]) - 0.5) * img_y
                    rob_x = cam_x + 0.155
                    rob_y = cam_y + 0.28
                    rob_z = cam_z - 0.195
                    base_angle = math.atan2(rob_x, rob_z)/math.pi*180
                    head_angle = math.atan2(rob_y, rob_z)/math.pi*180
                    self.robot.m1.goal_position = 45 - base_angle
                    self.robot.m5.goal_position = self.rest[4] - head_angle
                if self.short:
                    self.count += 1
                    if self.count == 5:
                        self.stop()

        def teardown(self):
            if self.cap.isOpened():
                self.cap.release()
            self.short = False
            for m in self.robot.motors:
                m.led = 'off'


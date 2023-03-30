"""
Start up the blossom webserver, CLI client, and web client.
"""

# make sure that prints will be supported
from __future__ import print_function

import sys
import subprocess
import argparse
import os
import shutil
import signal
from config import RobotConfig
from src import robot, sequence
from src.server import server
from src import server as srvr
import threading
import webbrowser
import re
from serial.serialutil import SerialException
from pypot.dynamixel.controller import DxlError
import random
import time
import uuid
import requests
import logging
from flask import Flask
from flask_cors import CORS
# seed time for better randomness
random.seed(time.time())

# turn off Flask logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# main robot
master_robot = None
# list of robots
robots = []
second_robot = None
# speed factor to playback sequences
speed = 1.0
# amplitude factor
amp = 1.0
# posture factor
post = 0.0

# yarn process (for web/UI stuff)
yarn_process = None

# CLI prompt
prompt = "(l)ist sequences / (s)equence play / (q)uit: "

loaded_seq = []

global talking 
talking = 'idle'

command = "sudo chmod -R 777 /dev/ttyUSB0"
password = '123456789'
os.system('echo %s | sudo -S %s' % (password, command))
command = "sudo chmod -R 777 /dev/ttyUSB1"
os.system('echo %s | sudo -S %s' % (password, command))

app = Flask(__name__)
CORS(app)

@app.route('/')
def hello_world():
    return 'hello world'

@app.route('/start_talk')
def start_talking():
    global talking
    talking = 'talk'
    return 'starting talk'

@app.route('/stop')
def stop_talking():
    global talking
    talking = 'idle'
    return 'stopped'

@app.route('/reset')
def reset_robot():
    global talking
    talking = 'reset'
    return 'reset robot joints'

def robot_talk_motion(event):
    global talking
    while True:
        if event.is_set():
            break
        elif(talking=='talk'):
            seq = random.choice(['happy_dance', 'happy_dancing', 'happy_nodding', 'happy', 'happy_daydream'])
            run_sequence(master_robot, seq)
        elif(talking=='reset'):
            run_sequence(master_robot, 'reset')
        else:
            seq = random.choice(['sesame/sesame1', 'sesame/sesame2', 'sesame/sesame3'])
            run_sequence(master_robot, seq)


class SequenceRobot(robot.Robot):
    """
    Robot that loads, plays, and records sequences
    Extends Robot class
    """

    def __init__(self, name, config):
        # init robot
        
        br=57600
        super(SequenceRobot, self).__init__(config, br, name)
        # save configuration (list of motors for PyPot)
        self.config = config
        # threads for playing and recording sequences
        self.seq_thread = self.seq_stop = None
        self.rec_thread = self.rec_stop = None
        # load all sequences for this robot
        self.load_seq()

        # speed, amp range from 0.5 to 1.5
        self.speed = 1.0
        self.amp = 1.0
        # posture ranges from -100 to 100
        self.post = 0.0

    def load_seq(self):
        """
        Load all sequences in robot's directory
        TODO - clean this up - try glob or os.walk
        """
        # get directory
        seq_dir = './src/sequences/%s' % self.name
        # make sure that directory for robot's seqs exist
        if not os.path.exists(seq_dir):
            os.makedirs(seq_dir)

        # iterate through sequences
        seq_names = os.listdir(seq_dir)
        seq_names.sort()
        # bar = Bar('Importing sequences',max=len(seq_names),fill='=')
        for seq in seq_names:
            # bar.next()
            subseq_dir = seq_dir + '/' + seq

            # is sequence, load
            if (seq[-5:] == '.json' and subseq_dir not in loaded_seq):
                # print("Loading {}".format(seq))
                self.load_sequence(subseq_dir)
                # loaded_seq.append(subseq_dir)

            # is subdirectory, go in and load all sequences
            # skips subdirectory if name is 'ignore'
            elif os.path.isdir(subseq_dir) and not ('ignore' in subseq_dir):
                # go through all sequence
                for s in os.listdir(subseq_dir):
                    # is sequence, load
                    seq_name = "%s/%s"%(subseq_dir,s)
                    if (s[-5:] == '.json' and seq_name not in loaded_seq):
                        # print("Loading {}".format(s))
                        self.load_sequence(seq_name)
                        # loaded_seq.append(seq_name)
        # bar.finish()

    def assign_time_length(self, keys, vals):
        timeMap = [None] * len(keys)
        for i in range(0, len(keys)):
            frameLst = vals[i].frames
            if len(frameLst)!= 0:
                timeAmnt = frameLst[-1].millis
                timeMap[i] = [keys[i], str(timeAmnt / 1000)]
        return timeMap

    def get_time_sequences(self):
        tempKeys = list(self.seq_list.keys())
        tempVals = list(self.seq_list.values())
        tempMap = self.assign_time_length(tempKeys, tempVals)
        return tempMap

    def get_sequences(self):
        """
        Get all sequences loaded on robot
        """
        return self.seq_list.keys()

    def play_seq_json(self, seq_json):
        """
        Play a sequence from json
        args:
            seq_json    sequence raw json
        returns:
            the thread setting motor position in the sequence
        """
        seq = sequence.Sequence.from_json_object(seq_json, rad=True)
        # create stop flag object
        self.seq_stop = threading.Event()

        # start playback thread
        self.seq_thread = robot.sequence.SequencePrimitive(
            self, seq, self.seq_stop, speed=speed, amp=amp, post=post)
        self.seq_thread.start()

        # return thread
        return self.seq_thread

    def play_recording(self, seq, idler=False, speed=speed, amp=amp, post=post):
        """
        Play a recorded sequence
        args:
            seq     sequence name
            idler   whether to loop sequence or not
        returns:
            the thread setting motor position in the sequence
        """
        print('playing recording ' + talking)
        self.seq_stop = threading.Event()

        # loop if idler
        if ('idle' in seq):
            seq = seq.replace('idle', '').replace(' ', '').replace('/', '')
            idler = True

        # start playback thread
        self.seq_thread = robot.sequence.SequencePrimitive(
            self, self.seq_list[seq], self.seq_stop, idler=idler, speed=self.speed, amp=self.amp, post=self.post)      
        self.seq_thread.start()
        # return thread
        return self.seq_thread

    def start_recording(self):
        """
        Begin recording a sequence
        """
        # create stop flag object
        self.rec_stop = threading.Event()

        # start recording thread
        self.rec_thread = robot.sequence.RecorderPrimitive(self, self.rec_stop)
        self.rec_thread.start()

def run_sequence(bot, seq):
    # play the sequence if it exists
    #if seq in robot.seq_list:
    # print("Playing sequence: %s"%(args[0]))
    # iterate through all robots
    #seq = random.choice(['sad_sigh', 'happy_dance'])
    if not bot.seq_stop:
        bot.seq_stop = threading.Event()
    bot.seq_stop.set()
    seq_thread = bot.play_recording(seq, idler=False)
    while (seq_thread.is_alive()):
        # sleep necessary to smooth motion
        time.sleep(0.1)
        continue
    # go into idler
    # if (idle_seq != ''):
    #     while (seq_thread.is_alive()):
    #         # sleep necessary to smooth motion
    #         time.sleep(0.1)
    #         continue
    #     for bot in robots:
    #         if not bot.seq_stop:
    #             bot.seq_stop = threading.Event()
    #         bot.seq_stop.set()
    #         bot.play_recording(idle_seq, idler=True)

last_cmd,last_args = 'rand',[]

def record(robot):
    """
    Start new recording session on the robot
    """
    # stop recording if one is happening
    if not robot.rec_stop:
        robot.rec_stop = threading.Event()
    # start recording thread
    robot.rec_stop.set()
    robot.start_recording()


def stop_record(robot, seq_name=""):
    """
    Stop recording
    args:
        robot       the robot under which to save the sequence
        seq_name    the name of the sequence
    returns:
        the name of the saved sequence
    """
    # stop recording
    robot.rec_stop.set()

    # if provided, save sequence name
    if seq_name:
        seq = robot.rec_thread.save_rec(seq_name, robots=robots)
        store_gesture(seq_name, seq)
    # otherwise, give it ranodm remporary name
    else:
        seq_name = uuid.uuid4().hex
        robot.rec_thread.save_rec(seq_name, robots=robots, tmp=True)

    # return name of saved sequence
    return seq_name


def store_gesture(name, sequence, label=""):
    """
    Save a sequence to GCP datastore
    args:
        name: the name of the sequence
        sequence: the sequence dict
        label: a label for the sequence
    """
    url = "https://classification-service-dot-blossom-gestures.appspot.com/gesture"
    payload = {
        "name": name,
        "sequence": sequence,
        "label": label,
    }
    requests.post(url, json=payload)


'''
Main Code
'''

def main(args):
    """
    Start robots, start up server, handle CLI
    """
    # get robots to start
    global master_robot
    global robots

    # use first name as master
    configs = RobotConfig().get_configs(args.names)
    print(configs)
    master_robot = safe_init_robot(args.names[0], configs[args.names[0]])
    configs.pop(args.names[0])
    # start robots
    robots = [safe_init_robot(name, config)
              for name, config in configs.items()]
    robots.append(master_robot)

    master_robot.reset_position()

    #master_robot.goto_position(screen_pos, 100)
    event = threading.Event()
    th = threading.Thread(target=robot_talk_motion, args=(event, )).start()

    #print(master_robot.get_sequences())

    #master_robot.play_recording('fear')
    
    #handle_input(master_robot,'s',['sad_sigh', 'reset'])

    app.run(port=5700)

    event.set()
    th.join()
    # start CLI
    #start_cli(master_robot)
    # start server
    #start_server(args.host, args.port, args.browser_disable)


def safe_init_robot(name, config):
    """
    Safely start/init robots, due to sometimes failing to start motors
    args:
        name    name of the robot to start
        config  the motor configuration of the robot
    returns:
        the started SequenceRobot object
    """
    # SequenceRobot
    bot = None
    # limit of number of attempts
    attempts = 10

    # keep trying until number of attempts reached
    while bot is None:
        try:
            bot = SequenceRobot(name, config)
        except (DxlError, NotImplementedError, RuntimeError, SerialException) as e:
            if attempts <= 0:
                raise e
            print(e, "retrying...")
            attempts -= 1
    return bot

def parse_args(args):
    """
    Parse arguments from starting in terminal
    args:
        args    the arguments from terminal
    returns:
        parsed arguments
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--names', '-n', type=str, nargs='+',
                        help='Name of the robot.', default=["woody"])
    parser.add_argument('--port', '-p', type=int,
                        help='Port to start server on.', default=8000)
    parser.add_argument('--host', '-i', type=str, help='IP address of webserver',
                        default=srvr.get_ip_address())
    parser.add_argument('--browser-disable', '-b',
                        help='prevent a browser window from opening with the blossom UI', 
                        action='store_true')
    parser.add_argument('--list-robots', '-l',
                        help='list all robot names', action='store_true')
    return parser.parse_args(args)


"""
Generic main handler
"""
if __name__ == "__main__":
    main(parse_args(sys.argv[1:]))

# use picamera2 instead of PiGear
from picamera2.picamera2 import Picamera2
from vidgear.gears import NetGear
from gpiozero import Servo, OutputDevice, Motor
from gpiozero.pins.pigpio import PiGPIOFactory
import datetime
import multiprocessing
import numpy as np
from copy import deepcopy
import logging
import json

# Initialize logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

class L298N_Motor:
    """
    Improved class for DC motor control via L298N driver with enhanced initialization and error handling.
    """
    def __init__(self, forward_pin, backward_pin, enable_pin=None, pigiofactory=False):
        factory = PiGPIOFactory() if pigiofactory else None
        self.motor = Motor(forward=forward_pin, backward=backward_pin, enable=enable_pin, pin_factory=factory)

    def set_value(self, speed):
        if speed > 0:
            self.motor.forward(speed)
        elif speed < 0:
            self.motor.backward(-speed)
        else:
            self.motor.stop()

    def close(self):
        self.motor.close()

class MyServo:
    def __init__(self, pin, initial_value=0, min_pulse_width=0.0005, max_pulse_width=0.0025, frame_width=0.02, pigiofactory=False):
        factory = PiGPIOFactory() if pigiofactory else None
        self.servo = Servo(pin, initial_value=initial_value, min_pulse_width=min_pulse_width, max_pulse_width=max_pulse_width, frame_width=frame_width, pin_factory=factory)

    def set_value(self, value):
        self.servo.value = value

    def close(self):
        self.servo.close()

class MyOutputDevice:
    def __init__(self, pin, active_high=True, initial_value=False, pigiofactory=False):
        factory = PiGPIOFactory() if pigiofactory else None
        self.output_device = OutputDevice(pin, active_high=active_high, initial_value=initial_value, pin_factory=factory)
    
    def set_value(self, value):
        self.output_device.value = value

    def close(self):
        self.output_device.close()

class GPIOController:
    def __init__(self, config_json):
        self.config = {'Last_setup_Time_ID': None}
        self.Last_command_Time_ID = None
        self.devices = {}
        self.update_config(config_json)

    def _setup_gpio(self):
        self.close_all_devices()
        logging.info(f'Output set with= {self.config}')
        for device_name, device_settings in self.config['GPIO_setups'].items():
            mode = device_settings['mode']
            config_kwargs = device_settings['config_kwargs']
            if mode == 'Servo':
                self.devices[device_name] = MyServo(**config_kwargs)
            elif mode == 'OutputDevice':
                self.devices[device_name] = MyOutputDevice(**config_kwargs)
            elif mode == 'L298N_Motor':
                self.devices[device_name] = L298N_Motor(**config_kwargs)

    def close_all_devices(self):
        logging.info(f'Closing all devices... {self.devices}')
        for each_device in self.devices:
            self.devices[each_device].close()

    def update_config(self, new_config_json):
        if 'GPIO_command' in new_config_json:
            self.config['GPIO_command'] = new_config_json['GPIO_command']
            self.config['Last_command_Time_ID'] = new_config_json['CTime_ID']
            if new_config_json['GPIO_command'] is not None:
                self.control()
        if 'GPIO_setups' in new_config_json and new_config_json['CTime_ID'] != self.config['Last_setup_Time_ID']:
            self.config['GPIO_setups'] = new_config_json['GPIO_setups']
            self.config['Last_setup_Time_ID'] = new_config_json['CTime_ID']
            self._setup_gpio()

    def control(self):
        if self.Last_command_Time_ID != self.config['Last_command_Time_ID']:
            self.Last_command_Time_ID = self.config['Last_command_Time_ID']
            logging.info(self.config['Last_command_Time_ID'])
        for device_name, action in self.config['GPIO_command'].items():
            if device_name in self.devices:
                if isinstance(action, (int, float)) and -1 <= action <= 1:
                    self.devices[device_name].set_value(action)
                else:
                    logging.error(f'Invalid action for device {device_name}: {action}')
            else:
                logging.error(f'Unknown device: {device_name}')

def GPIO_process(gpio_input):
    gpio_controller = GPIOController(deepcopy(gpio_input['received_data']))
    while True:
        local_received = deepcopy(gpio_input['received_data'])
        gpio_controller.update_config(local_received)

def video_process(video_input):
    try:
        # Initialize picamera2
        picamera2 = Picamera2()
        video_size = (video_input['camera_config']['size'][0], video_input['camera_config']['size'][1])
        preview_config = picamera2.create_preview_configuration(main={"size": video_size, "format": video_input['camera_config']['format']})
        picamera2.configure(preview_config)
        picamera2.start()
        while video_input['commands'] != 'STOP_video_process':
            video_input['video_frame'] = picamera2.capture_array()
    finally:
        picamera2.stop()

def server_data_process(sdv_input):
    def server_connect():
        # server = NetGear(address=sdv_input['server_ip'], port="58954", protocol="tcp", source=None, logging=True, bidirectional_mode=True)
        server = NetGear(address=sdv_input['netgear_options']['address'], port=sdv_input['netgear_options']['port'],
                          protocol=sdv_input['netgear_options']['protocol'], source=None, logging=sdv_input['netgear_options']['logging'],
                            bidirectional_mode=sdv_input['netgear_options']['bidirectional_mode'])
        return server

    server = server_connect()
    last_recv_data = None
    while True:
        try:
            if sdv_input['commands'] == 'STOP_server':
                server.close()
                break
            Time_ID = datetime.datetime.now()
            data_for_client = {'STime_ID': str(Time_ID), 'message': 'Hello, I am a Server.', 'gpio_data': sdv_input['gpio_data_to_send']}
            if sdv_input['video_frame'] is None:
                sdv_input['video_frame'] = np.array(np.zeros((480, 640, 3)), dtype=np.uint8)

            recv_data = server.send(frame = sdv_input['video_frame'], message=data_for_client)
            if recv_data and recv_data != last_recv_data:
                logging.info(f'Server data process -> {recv_data}')
                last_recv_data = recv_data
                sdv_input['received_data'] = recv_data
        except Exception as exp:
            logging.error(exp)
            server.close()
            if '[NetGear:ERROR] :: Client(s) seems to be offline, Abandoning.' in str(exp):
                logging.info('Reloading server.')
                server = server_connect()
            else:
                break


if __name__ == '__main__':

    with open('config.json', 'r') as file:
        configs = json.load(file)

    manager = multiprocessing.Manager()
    mp_variable = manager.dict(video_frame=None, gpio_data_to_send=None, commands=None, received_data={})
    mp_variable['netgear_options'] = configs["netgear_options"]
    mp_variable['camera_config'] = configs["camera_config"]

    processes = [
        multiprocessing.Process(target=server_data_process, args=(mp_variable,)),
        multiprocessing.Process(target=video_process, args=(mp_variable,)),
        multiprocessing.Process(target=GPIO_process, args=(mp_variable,))
    ]

    for p in processes:
        p.start()

    input("Press Enter to terminate the processes...\n")

    for p in processes:
        p.terminate()
        p.join()

    logging.info("Processes terminated.")

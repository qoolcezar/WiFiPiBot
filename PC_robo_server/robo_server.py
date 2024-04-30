from vidgear.gears import NetGear
import numpy as np
import cv2
import multiprocessing
import datetime
from controller import Controller, ControllerTransformer
import time
import json

def controller_process(shared_variable):
    controls_GPIO = shared_variable['controls_GPIO']
    controller = Controller()
    ctrltrans = ControllerTransformer(controls_GPIO)

    while True:
        controller.process_events()
        ctrl_proc_msg = {
            'CTime_ID': datetime.datetime.now().isoformat(),
            'GPIO_command': ctrltrans.transform_ep(controller.last_event) if controller.last_event else ctrltrans.last_transformed_values
        }
        shared_variable['ctrl_proc_msg'] = ctrl_proc_msg
        print(ctrl_proc_msg)

def client_data_process(shared_variable):
    def client_connect():
        netgear_options = shared_variable['netgear_options']
        GPIO_setups = shared_variable['GPIO_setups']
        client = NetGear(**netgear_options)
        received_data = client.recv(return_data=shared_variable['ctrl_proc_msg'])
        if received_data:
            shared_variable['ctrl_proc_msg'] = {'CTime_ID':f'{datetime.datetime.now()}','GPIO_setups': GPIO_setups}
        return client
    
    client = client_connect()    
    last_received_data = datetime.datetime.now()

    while True:
        received_data = client.recv(return_data=shared_variable['ctrl_proc_msg'])
        if received_data:
            last_received_data = datetime.datetime.now()
            other_received_data, frame = received_data
            frame = frame if frame is not None else np.zeros((480, 640, 3))
            frame = frame[::-1, ::-1, :]    # rotate frame
            cv2.imshow("Robo Output Frame", frame)
        else:
            print('Waiting for data from server...')
            if datetime.datetime.now() > last_received_data + datetime.timedelta(seconds=5):
                print(f"Waiting for server for 1 seconds and reconnecting NetGear...")
                time.sleep(1)
                client = client_connect() 

        # check for 'q' key to quit
        if cv2.waitKey(1) == ord('q'):
            break

    cv2.destroyAllWindows()

def main():

    with open('configs.json', 'r') as file:
        configs = json.load(file)

    manager = multiprocessing.Manager()
    shared_variable = manager.dict()

    shared_variable['ctrl_proc_msg'] = None
    shared_variable['netgear_options'] = configs["netgear_options"]
    shared_variable['GPIO_setups'] = configs["GPIO_setups"]
    shared_variable['controls_GPIO'] = configs["controls_GPIO"]

    processes = [
        multiprocessing.Process(target=client_data_process, args=(shared_variable,)),
        multiprocessing.Process(target=controller_process, args=(shared_variable,))
    ]

    for process in processes:
        process.start()

    input("Press Enter to terminate the processes...\n")

    for process in processes:
        process.terminate()
        process.join()

    print("Processes terminated.")

if __name__ == '__main__':
    main()

# Modified from https://inputs.readthedocs.io/en/latest/user/examples.html
# ControllerTransformer returns device_name instead of pin
# add in ControllerTransformer XYfunct that is triggered by 2 different controlls

import inputs
from functools import partial
import time
import importlib

def get_value_from_nested_dict(nested_dict, target_key):
    for key, value in nested_dict.items():
        if isinstance(value, dict):
            if target_key in value:
                return key, value[target_key]
    return None

class Controller(object):
    def __init__(self, gamepad=None):
        self.controls_states = {}
        self.last_event = {}
        self.gamepad = gamepad
        if not gamepad:
            self._get_gamepad()

    def _get_gamepad(self):
        """Get a gamepad object."""
        while True:
            importlib.reload(inputs)
            try:
                self.gamepad = inputs.devices.gamepads[0]
                break
            except IndexError:
                print("No gamepad found.")
                time.sleep(1)

    def add_unknown_event(self, event, key):
        """Deal with unknown events."""
        if event.ev_type == 'Key' or event.ev_type == 'Absolute':
            self.controls_states[key] = event.state
        else:
            return

    def process_event(self, event):
        """Process the event into a state."""
        if event.ev_type == 'Sync':
            return
        if event.ev_type == 'Misc':
            return
        key = event.ev_type + '-' + event.code
        try:
            self.controls_states[key] = event.state
        except KeyError:
            self.add_unknown_event(event, key)
        return {key : event.state}

    def process_events(self):
        """Process available events."""
        try:
            events = self.gamepad.read()
        except EOFError:
            events = []
        except inputs.UnpluggedError:
            print("Gamepad disconnected")
            time.sleep(1)
            return
        for event in events:
            self.last_event = self.process_event(event)

class ControllerTransformer(object):
    def __init__(self, transform_json):
        self.transform_json = transform_json
        self.last_transformed_values = {}
        self._prepare_transform_json()

    def normalization_func(self, key_value, ctrl_json):
        return ctrl_json['output_range']["min"] + (key_value[1] - ctrl_json['ctrl_range']['min']) / (ctrl_json['ctrl_range']["max"] - ctrl_json['ctrl_range']['min']) * (ctrl_json['output_range']["max"] - ctrl_json['output_range']["min"])
    
    def exact_func(self, key_value):
        return key_value[1]

    class XY_transformation(object):
        def __init__(self):
            self.ctrl_json = {}
            self.X_value = 0
            self.Y_value = 0
            self.max_turn_L = 0
            self.max_turn_R = 0
            self.return_name_prefix = ''

        def normalization_func(self, value, ctrl_json):
            return ctrl_json['output_range']["min"] + (value - ctrl_json['ctrl_range']['min']) / (ctrl_json['ctrl_range']["max"] - ctrl_json['ctrl_range']['min']) * (ctrl_json['output_range']["max"] - ctrl_json['output_range']["min"])

        def XY_transformed(self, key_value = None, ctrl_json = None):
            if ctrl_json is not None:
                self.ctrl_json.update(ctrl_json)
                name, axis = get_value_from_nested_dict(ctrl_json, 'XYfunct_axis')
                if axis == 'X':
                    self.X_name = name
                elif axis == 'Y':
                    self.Y_name = name
                _, max_turn_LR = get_value_from_nested_dict(ctrl_json, 'max_turn_LR')
                self.max_turn_L, self.max_turn_R = max_turn_LR
                _, self.return_name_prefix = get_value_from_nested_dict(ctrl_json, 'return_name')
                return

            if self.X_name == key_value[0]:
                self.X_value = self.normalization_func(key_value[1], self.ctrl_json[key_value[0]])
                
            elif self.Y_name == key_value[0]:
                self.Y_value = self.normalization_func(key_value[1], self.ctrl_json[key_value[0]])

            if self.X_value >= 0:
                if self.Y_value >= 0:
                    return {f"{self.return_name_prefix}_Left": self.Y_value, f"{self.return_name_prefix}_Right": self.Y_value - self.max_turn_R * self.X_value}
                else:
                    return {f"{self.return_name_prefix}_Left": self.Y_value, f"{self.return_name_prefix}_Right": self.Y_value + self.max_turn_R * self.X_value}
            else:
                if self.Y_value >= 0:
                    return {f"{self.return_name_prefix}_Left": self.Y_value + self.max_turn_L * self.X_value,f"{self.return_name_prefix}_Right": self.Y_value}
                else:
                    return {f"{self.return_name_prefix}_Left": self.Y_value - self.max_turn_L * self.X_value, f"{self.return_name_prefix}_Right": self.Y_value}



    def _prepare_transform_json(self):
        temp_functions = {}
        for each in self.transform_json:
            if self.transform_json[each]['used_funct'] == "normalization_func":
                self.transform_json[each]['funct'] = partial(self.normalization_func, ctrl_json=self.transform_json[each])
            elif self.transform_json[each]['used_funct'] == "exact_func":
                self.transform_json[each]['funct'] = partial(self.exact_func)
            elif self.transform_json[each]['used_funct'] == "XYfunct":
                if self.transform_json[each]['return_name'] not in temp_functions:
                    temp_functions[self.transform_json[each]['return_name']] = ControllerTransformer.XY_transformation().XY_transformed
                if self.transform_json[each]['return_name'] in temp_functions:
                    self.transform_json[each]['funct'] = temp_functions[self.transform_json[each]['return_name']]
                    self.transform_json[each]['funct'](ctrl_json={each: self.transform_json[each]})
            

    def transform_ke(self, event_dict):
        # returns key-event, where event is transformed trough funct defined
        for key, value in event_dict.items():
            if key not in self.transform_json:
                transformed_value = value
                self.last_transformed_values[key] = transformed_value
                return {key: transformed_value}
            elif 'funct' in self.transform_json[key]:
                transformed_value = self.transform_json[key]['funct'](value)
                self.last_transformed_values[key] = transformed_value
                return {key: transformed_value}
            
    def transform_ep(self, event_dict):
        # returns key-event, where key is the return_name defined and event is transformed trough funct defined
        for key, value in event_dict.items():
            if key in self.transform_json:
                transformed_value = self.transform_json[key]['funct']((key, value))
                if "return_only_value" in self.transform_json[key] and self.transform_json[key]["return_only_value"]:
                    self.last_transformed_values.update(transformed_value)
                    return transformed_value
                self.last_transformed_values[self.transform_json[key]['return_name']] = transformed_value
                return {self.transform_json[key]['return_name']: transformed_value}

def main():
    GPIO_ctrls = {
        "Absolute-ABS_RX": {
            "ctrl_range": {"min": -32768,
                        "max": 32768},
            "return_name" : "servo_horizontal",
            "description": "not continous servo motor with range from 0 to 180 degrees",
            "output_range": {"min": 1,
                            "max": -1},
            "used_funct": "normalization_func"
        },
        "Absolute-ABS_RY": {
            "ctrl_range": {"min": -32768,
                        "max": 32768},
            "return_name" : "servo_vertical",
            "description": "not continous servo motor with range from 0 to 180 degrees",
            "output_range": {"min": -1,
                            "max": 1},
            "used_funct": "normalization_func"
        },
        "Key-BTN_WEST": {
            "return_name" : "led_blue",
            "used_funct": "exact_func"
        },
        "Key-BTN_EAST": {
            "return_name" : "led_red",
            "used_funct": "exact_func"
        },
        "Absolute-ABS_X": {
            "description": "Works in conjunction with Absolute-ABS_Y controller axis. Utilizing XYfunct, it controls Left and Right driver wheels. XYfunct requires the same return_name to correlate with the other controller axis. It will return {'return_name': {'return_name_Left': output_range, 'return_name_Right': output_range } }. The max_turn_LR pair must be identical for both axes.",
            "ctrl_range": {"min": -32768,
                        "max": 32768},
            "output_range": {"min": -1,
                            "max": 1},
            "return_name" : "wheels",
            "used_funct": "XYfunct",
            "XYfunct_axis": "X",
            "max_turn_LR": [1, 1],
            "return_only_value": True
        },
        "Absolute-ABS_Y": {
            "description": "Works in conjunction with Absolute-ABS_X controller axis. Utilizing XYfunct, it controls Left and Right driver wheels. XYfunct requires the same return_name to correlate with the other controller axis. It will return {'return_name': {'return_name_Left': output_range, 'return_name_Right': output_range } }. The max_turn_LR pair must be identical for both axes.",
            "ctrl_range": {"min": -32768,
                        "max": 32768},
            "output_range": {"min": -1,
                            "max": 1},
            "return_name" : "wheels",
            "used_funct": "XYfunct",
            "XYfunct_axis": "Y",
            "max_turn_LR": [1, 1],
            "return_only_value": True
        }
        }

    print("Testing only controller functionality")

    """Process all events forever."""
    controller = Controller()
    ctrltrans = ControllerTransformer(GPIO_ctrls)
    while True:
        controller.process_events()
        if controller.last_event is not None:
            print('-------------')
            print(f'controller.last_event=> {controller.last_event}')
            print(f'controller.controls_state=> {controller.controls_states}')
            transformed_last_event = ctrltrans.transform_ep(controller.last_event)
            print(f'transformed_last_event= {transformed_last_event}')
            print(f'last_transformed_values= {ctrltrans.last_transformed_values}')
            print('-------------')

if __name__ == "__main__":
    main()
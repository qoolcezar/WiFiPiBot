# WiFiPiBot
## Description
WiFiPiBot transforms a Raspberry Pi 3B+ into a WiFi-controlled robot using the Raspberry Camera Module v3 and DS4Windows for console controller connectivity. Enhanced by the NetGear library, it offers precise remote operation and interactive control.
## Installation
### PC configurtation

Follow these steps to configure your Windows machine using a clean Conda environment with Python 3.11:

1. **Install DS4Windows**:
   - Download and start DS4Windows to enable controller support on Windows. Get it from [DS4Windows Official Site](https://ds4-windows.com/).
   - Connect your controller to the PC and observe in the DS4Windows application that is working ok.

2. **Create a Conda Environment** (Optional):

   If you prefer to use a Conda environment, create one specifically for this project:
   ```bash
    conda create -n yourenvname python=3.11
    conda activate yourenvname
   ```

4. **Install Python Packages** :
   ```bash
    pip install inputs
    pip install vidgear
    pip install opencv-python
    pip install pyzmq
    pip install simplejpeg
    ```
5. **Test Controller Connectivity** :
   Run the controller.py script to check if the controller is connected properly
   ```bash
   python controller.py
   ```
6. **Final configurations** :  
   Config the `configs.json` file.
- In the `netgear_options`, enter the PC's IP address to which the Raspberry Pi robot should connect.
- In the `GPIO_setups` - GPIO configs of the RaspberryPi robot, update the entries with your specific setup.
- In the `controls_GPIO` - controller to GPIO mapping , update the entries with your specific setup.


### RaspberryPi configurtation

Follow these steps to set up your Raspberry Pi with the Camera Module v3:

1. **Install Debian Bookworm x64**
2. **Increase SWAP File**
    ```bash
    sudo nano /etc/dphys-swapfile
    
    # Change the following line:
    CONF_SWAPSIZE=4096
    # Save changes
    
    sudo reboot
    ```
3. **Update and Upgrade System Packages**
    ```bash
    sudo apt-get update
    sudo apt-get upgrade
    ``` 
4. **Test the Camera Module v3**
   Check if the camera is working properly (no additional configuration needed in raspi-config)
    ```bash
    libcamera-hello --qt-preview -t0
    ``` 
5. **Install Dependencies**
  Install necessary Python packages. Note: You might encounter an externally-managed-environment error, which you can bypass at your own risk by using the --break-system-packages flag:
    ```bash
    pip install vidgear
    pip install pyzmq
    ```
For x86 Bookworm and Legacy/Bullseye, see below!
  
6. **Enable pigpio Service Daemon** 
  Set up the pigpio service daemon to start on boot
    ```bash
    # Create a service file:
    sudo nano /etc/systemd/system/pigpiod.service
    ```
    Paste the following into the file:
    ```bash
    [Unit]
    Description=Pigpio daemon
    After=network.target
    
    [Service]
    ExecStartPre=/bin/sleep 30
    ExecStart=/usr/bin/pigpiod -l -n localhost
    Type=forking
    
    [Install]
    WantedBy=multi-user.target
    ```
    Reload the daemon, enable and start the service:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable pigpiod.service
    sudo systemctl start pigpiod.service
    sudo reboot
    ```

7. **Final Configurations**   
   Config the `config.json` file.
- In the `netgear_options`, enter the PC's IP address to which the Raspberry Pi robot should connect.
- In the `camera_config`, enter the desired resolution size.
  
***For x86 Bookworm***
```bash
sudo apt-get install python3-opencv
sudo apt-get install build-essential cmake pkg-config libjpeg-dev libtiff5-dev libjasper-dev libpng-dev libavcodec-dev libavformat-dev libswscale-dev libv4l-dev libxvidcore-dev libx264-dev libgtk-3-dev libatlas-base-dev gfortran
pip install vidgear
pip install pyzmq
```
***For x86 Legacy/Bullseye***
```bash
sudo apt-get install build-essential cmake pkg-config libjpeg-dev libtiff5-dev libjasper-dev libpng-dev libavcodec-dev libavformat-dev libswscale-dev libv4l-dev libxvidcore-dev libx264-dev libgtk-3-dev libatlas-base-dev gfortran
sudo apt-get install python3-opencv
sudo apt-get install libopenblas-base
pip install pyzmq
pip install vidgear
pip install --upgrade numpy
```
## Usage

1. Start DS4Windows and connect controller to it
2. Start the robo_server.py from PC
3. Start the robo_client.py from RaspberryPi

ENJOY!

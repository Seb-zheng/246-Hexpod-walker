#!/usr/bin/python3
import sys
import time
import os
import tty      
import termios  
import select    
import warnings 

# Ignore gpiozero PWM software fallback warnings
warnings.filterwarnings("ignore", module="gpiozero") 

# ===== Hardware-Level PWM Setup (Anti-Jitter) =====
from gpiozero import Device
from gpiozero.pins.lgpio import LGPIOFactory
# Force gpiozero to use lgpio for precise hardware timing (eliminates servo jitter)
Device.pin_factory = LGPIOFactory()

from gpiozero import Servo, DistanceSensor

# ===== Pin Definitions (BCM Numbering) =====
TILT_PIN = 4
BR_PIN = 21
BL_PIN = 6
HEAD_PIN = 26
TRIG_PIN = 23
ECHO_PIN = 24

# ===== Sensor & Actuator Initialization =====
# DistanceSensor automatically handles ultrasonic timing and calculations
sonar = DistanceSensor(echo=ECHO_PIN, trigger=TRIG_PIN, max_distance=2.0)

# Initialize servos with standard pulse width range (500us to 2500us)
tilt_servo = Servo(TILT_PIN, min_pulse_width=0.0005, max_pulse_width=0.0025)
br_servo   = Servo(BR_PIN, min_pulse_width=0.0005, max_pulse_width=0.0025)
bl_servo   = Servo(BL_PIN, min_pulse_width=0.0005, max_pulse_width=0.0025)
head_servo = Servo(HEAD_PIN, min_pulse_width=0.0005, max_pulse_width=0.0025)

def set_pwm(servo_obj, us):
    """Map absolute microseconds (us) to gpiozero's duty cycle range [-1.0, 1.0]"""
    if us == 0:
        servo_obj.detach() # Stop PWM output, release servo torque
    else:
        # 1500us -> 0.0 (Neutral), 500us -> -1.0, 2500us -> 1.0
        val = (us - 1500) / 1000.0
        # Clamp values to prevent out-of-bounds errors
        val = max(-1.0, min(1.0, val))
        servo_obj.value = val

# ===== Gait Control Logic (Tilt-and-Swing Mechanism) =====
def backward():
    set_pwm(tilt_servo, 800) 
    time.sleep(0.15)
    set_pwm(bl_servo, 800)    
    time.sleep(0.15)
    set_pwm(tilt_servo, 2000)
    time.sleep(0.15)
    set_pwm(br_servo, 1800) 
    time.sleep(0.15)
    set_pwm(tilt_servo, 1500) 
    time.sleep(0.15)
    set_pwm(bl_servo, 1500)   
    time.sleep(0.15)
    set_pwm(br_servo, 1500)   
    time.sleep(0.15)

def forward():
    set_pwm(tilt_servo, 800) 
    time.sleep(0.15)
    set_pwm(bl_servo, 1800)       
    time.sleep(0.15)
    set_pwm(tilt_servo, 2000)
    time.sleep(0.15)
    set_pwm(br_servo, 800) 
    time.sleep(0.15)
    set_pwm(tilt_servo, 1500) 
    time.sleep(0.15)
    set_pwm(bl_servo, 1500)   
    time.sleep(0.15)
    set_pwm(br_servo, 1500)   
    time.sleep(0.15)

def left():
    set_pwm(tilt_servo, 800) 
    time.sleep(0.15)
    set_pwm(bl_servo, 1800)       
    time.sleep(0.15)
    set_pwm(tilt_servo, 2000)
    time.sleep(0.15)
    set_pwm(br_servo, 1800) 
    time.sleep(0.15)
    set_pwm(tilt_servo, 1500) 
    time.sleep(0.15)
    set_pwm(bl_servo, 1500)   
    time.sleep(0.15)
    set_pwm(br_servo, 1500)   
    time.sleep(0.15)

def right():
    set_pwm(tilt_servo, 800) 
    time.sleep(0.15)
    set_pwm(bl_servo, 800)    
    time.sleep(0.15)
    set_pwm(tilt_servo, 2000)
    time.sleep(0.15)
    set_pwm(br_servo, 800) 
    time.sleep(0.15)
    set_pwm(tilt_servo, 1500) 
    time.sleep(0.15)
    set_pwm(bl_servo, 1500)   
    time.sleep(0.15)
    set_pwm(br_servo, 1500)   
    time.sleep(0.15)
    
def stop():
    """Emergency stop: detach all leg servos"""
    set_pwm(tilt_servo, 0) 
    set_pwm(bl_servo, 0)   
    set_pwm(br_servo, 0)   
    time.sleep(0.15)

def obstacleDetected():
    """Evasion maneuver when an obstacle is detected"""
    for _ in range(5):
        backward()
    for _ in range(3):
        right()

def turnHead():
    """Sweep the ultrasonic sensor to scan the area"""
    set_pwm(head_servo, 700)
    time.sleep(0.5)
    set_pwm(head_servo, 2100)
    time.sleep(0.5)
    set_pwm(head_servo, 1500)
    time.sleep(0.5)

# ===== Operating Modes =====
def autoMode():
    """Autonomous navigation with obstacle avoidance"""
    print("\n🚀 Entering Auto Cruise Mode! (Press ANY KEY to interrupt)")
    
    # Save current terminal settings
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    
    try:
        # Enter raw mode for non-blocking keyboard listener
        tty.setraw(sys.stdin.fileno())
        
        while True:
            # 1. Non-blocking check for any key press
            if select.select([sys.stdin], [], [], 0.0)[0]:
                sys.stdin.read(1) # Consume the key
                break             # Exit the infinite loop immediately

            # 2. Execute single gait cycle and scan
            # Note: In raw mode, \r\n is required for proper carriage return
            print("\r\n🔍 Scanning environment...", end="")
            turnHead()
            time.sleep(0.5)
            
            # Convert default distance (meters) to centimeters
            distance_cm = round(sonar.distance * 100, 2)
            print(f"\r\n📏 Current Distance: {distance_cm} cm", end="")
            
            if 1 < distance_cm < 35:
                print("\r\n⚠️ Obstacle Detected! Executing evasion...", end="")
                obstacleDetected()
            else:
                print("\r\n✅ Path clear. Moving forward...", end="")
                forward()
                forward()
                forward()
            
            set_pwm(head_servo, 2100)
            time.sleep(0.5)
            
    finally:
        # Ensure terminal settings are restored regardless of how the loop exits
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        
    print("\n🛑 Interrupt received. Auto Mode terminated. Returning to Manual Mode.")
    stop()
    
# ===== Real-Time Interactive Control Layer =====
def getch():
    """Read a single keypress from the terminal (without pressing Enter)"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def flush_input():
    """Flush excess keystrokes from the buffer to prevent runaway loops"""
    while select.select([sys.stdin], [], [], 0.0)[0]:
        sys.stdin.read(1)

def interactiveMode():
    """Main control panel for manual operation"""
    print("\n" + "="*45)
    print("🤖 Robot Interactive Control Terminal Started 🤖")
    print("="*45)
    print(" [W] Forward            [S] Backward")
    print(" [A] Turn Left          [D] Turn Right")
    print(" [H] Turn Head          [Space] Stop")
    print(" [R] Run Auto Mode      [Q] Quit Program")
    print("="*45)
    print("Note: You can hold down W/A/S/D. Release to stop.\n")

    while True:
        char = getch().lower()
        
        if char == 'w':
            print("➡️ Command: Forward (W)")
            forward()
        elif char == 's':
            print("➡️ Command: Backward (S)")
            backward()
        elif char == 'a':
            print("➡️ Command: Left (A)")
            left()
        elif char == 'd':
            print("➡️ Command: Right (D)")
            right()
        elif char == 'h':
            print("➡️ Command: Turn Head (H)")
            turnHead()
        elif char == 'r':
            print("\n➡️ Command: Auto Mode Triggered (R)")
            autoMode()
        elif char == ' ':
            print("➡️ Command: Emergency Stop (Space)")
            stop()
        elif char == 'q' or char == '\x03':
            print("\n👋 Quit signal received. Shutting down...")
            break
        else:
            print(f"⚠️ Invalid Key: {char.upper()} (Please use W/A/S/D/H/R/Q)")
        
        # Crucial step: flush the buffer after executing the movement
        flush_input()

def main():
    # Program entry point: launch the interactive UI
    interactiveMode()

# ===== Execution and Cleanup =====
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Catch Ctrl+C force quits gracefully
        print("\n👋 KeyboardInterrupt received...")
    finally:
        # Guarantee that all GPIO resources are released and servos are powered down
        print("🧹 Cleaning up GPIO resources...")
        stop()
        tilt_servo.close()
        bl_servo.close()
        br_servo.close()
        head_servo.close()
        sonar.close()
        print("✅ Shutdown successful!")
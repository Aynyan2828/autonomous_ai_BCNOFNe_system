#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audio and Input Tester for shipOS
Run this directly to bypass systemd and see exact error messages.
"""

import os
import sys
import time
import subprocess
try:
    import evdev
except ImportError:
    print("Error: evdev module not installed. Run: pip install evdev")
    sys.exit(1)

def test_speaker():
    print("\n--- 1. Speaker Playback Test ---")
    # Using aplay directly to test ALSA
    test_file = "/usr/share/sounds/alsa/Front_Center.wav"
    if not os.path.exists(test_file):
        test_file = "/usr/share/sounds/purism/bell.ogg"
    
    if os.path.exists(test_file):
        print(f"Playing test sound ({test_file})...")
        if test_file.endswith(".ogg"):
            # Using paplay or aplay based on file type
            cmd = ["paplay", test_file]
        else:
            cmd = ["aplay", test_file]
            
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Playback command succeeded!")
            else:
                print("❌ Playback command failed!")
                print("Error Details:")
                print(result.stderr)
        except Exception as e:
            print(f"Failed to execute playback command: {e}")
    else:
        print("Test sound file not found, creating a simple beep...")
        os.system('speaker-test -t sine -f 440 -c 1 -s 1 -d 2')

def test_macropad():
    print("\n--- 2. Macro Pad Event Test ---")
    print("Press the Macro Pad buttons. Press Ctrl+C to stop.")
    
    # Try event12 as per config, or find it
    device_path = "/dev/input/event12"
    if not os.path.exists(device_path):
        print(f"Warning: {device_path} not found. Attempting to scan for devices...")
        found = False
        for path in evdev.list_devices():
            try:
                device = evdev.InputDevice(path)
                print(f"Found: {path} - {device.name}")
                if "USB" in device.name or "Composite" in device.name or "Pad" in device.name:
                    device_path = path
                    found = True
                    break
            except:
                pass
                
        if not found:
            print("❌ Could not automatically identify the Macro Pad. Is it connected?")
            return

    try:
        device = evdev.InputDevice(device_path)
        print(f"Listening to: {device.name} at {device_path}")
        print("Please press F13, F14, F15, F19, F20...")
        
        for event in device.read_loop():
            if event.type == evdev.ecodes.EV_KEY:
                key_event = evdev.categorize(event)
                if key_event.keystate == key_event.key_down:
                    print(f"✅ Key Pressed! Keycode: {key_event.keycode} (Raw Code: {event.code})")
    
    except PermissionError:
        print(f"❌ Permission Denied when accessing {device_path}.")
        print("Are you in the 'input' group? Are you running this script with proper rights?")
        print("Try running: sudo usermod -aG input pi")
    except Exception as e:
        print(f"❌ Error reading input device: {e}")

if __name__ == "__main__":
    try:
        test_speaker()
        test_macropad()
    except KeyboardInterrupt:
        print("\nTest stopped by user.")

#!/bin/bash

# Setup script for Raspberry Pi Codec Zero
# Based on official documentation

echo "Step 1: Installing dependencies..."
sudo apt-get update
sudo apt-get install -y git alsa-utils

echo "Step 2: Downloading Codec Zero configurations..."
cd /home/$USER
if [ ! -d "Pi-Codec" ]; then
    git clone https://github.com/raspberrypi/Pi-Codec.git
else
    echo "Pi-Codec repository already exists. Pulling latest..."
    cd Pi-Codec
    git pull
    cd ..
fi

echo "Step 3: Restoring ALSA state for Onboard MEMS Mic..."
# This enables the MEMS mic and Speaker playback
sudo alsactl restore -f /home/$USER/Pi-Codec/Codec_Zero_OnboardMIC_record_and_SPK_playback.state

echo "------------------------------------------------"
echo "Setup Complete!"
echo "------------------------------------------------"
echo "IMPORTANT CHECKS:"
echo "1. Ensure '/boot/firmware/config.txt' contains:"
echo "   dtoverlay=rpi-codeczero"
echo "   #dtparam=audio=on  (Commented out)"
echo ""
echo "2. If you are running headless (no desktop), you might need to create ~/.asoundrc:"
echo "   pcm.!default {"
echo "       type hw"
echo "       card Zero"
echo "   }"
echo ""
echo "3. Reboot your Pi after making changes to config.txt"

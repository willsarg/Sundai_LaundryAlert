#!/bin/bash

echo "=== Raspberry Pi Codec Zero Installation ==="
echo ""
echo "Step 1: Installing dependencies..."
sudo apt-get update
sudo apt-get install -y vim git alsa-utils

echo ""
echo "Step 2: Configuring /boot/config.txt for Codec Zero hardware..."
echo "Please add the following line to /boot/config.txt if not already present:"
echo "    dtoverlay=rpi-codeczero"
echo ""
read -p "Press Enter to edit /boot/config.txt (or Ctrl+C to skip if already configured)..."
sudo vim /boot/config.txt

echo ""
echo "Step 3: Cloning Pi-Codec repository..."
cd ~
if [ -d "Pi-Codec" ]; then
    echo "Pi-Codec directory already exists, skipping clone..."
else
    git clone https://github.com/raspberrypi/Pi-Codec
fi

echo ""
echo "Step 4: Setting up ALSA configuration..."
echo "Creating .asoundrc file for Codec Zero..."
cat > ~/.asoundrc << 'EOF'
pcm.!default {
    type hw
    card IQaudIOCODEC
}

ctl.!default {
    type hw
    card IQaudIOCODEC
}
EOF

echo ""
echo "Step 5: Selecting audio configuration..."
echo "Available Codec Zero configurations:"
echo "1. AUXIN_record_and_HP_playback - AUX input recording with headphone output"
echo "2. OnboardMIC_record_and_SPK_playback - Built-in microphone with speaker output"
echo "3. Playback_only - Audio playback configuration"
echo "4. StereoMIC_record_and_HP_playback - Stereo microphone with headphone output"
echo ""
read -p "Select configuration (1-4, default: 2): " choice

case $choice in
    1)
        STATE_FILE="Codec_Zero_AUXIN_record_and_HP_playback.state"
        ;;
    2|"")
        STATE_FILE="Codec_Zero_OnboardMIC_record_and_SPK_playback.state"
        ;;
    3)
        STATE_FILE="Codec_Zero_Playback_only.state"
        ;;
    4)
        STATE_FILE="Codec_Zero_StereoMIC_record_and_HP_playback.state"
        ;;
    *)
        echo "Invalid selection. Using default configuration."
        STATE_FILE="Codec_Zero_OnboardMIC_record_and_SPK_playback.state"
        ;;
esac

echo ""
echo "Loading configuration: $STATE_FILE"
sudo alsactl restore -f ~/Pi-Codec/$STATE_FILE

echo ""
echo "Step 6: Verifying installation..."
aplay -l

echo ""
echo "Step 7: Testing audio playback..."
if [ -f /usr/share/sounds/alsa/Front_Center.wav ]; then
    echo "Playing test sound..."
    aplay /usr/share/sounds/alsa/Front_Center.wav
else
    echo "Test sound file not found, skipping audio test."
fi

echo ""
echo "=== Codec Zero installation complete! ==="
echo "Configuration loaded: $STATE_FILE"
echo ""
echo "IMPORTANT: If you edited /boot/config.txt, you need to reboot:"
echo "    sudo reboot"
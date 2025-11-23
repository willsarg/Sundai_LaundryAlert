# Install build dependencies
sudo apt-get update
sudo apt-get install -y build-essential zlib1g-dev libncurses5-dev \
    libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev \
    libsqlite3-dev wget libbz2-dev liblzma-dev

# Download Python 3.12
cd /tmp
wget https://www.python.org/ftp/python/3.12.8/Python-3.12.8.tgz
tar -xf Python-3.12.8.tgz
cd Python-3.12.8

# Configure and compile (this will take 1-2 hours on a Pi)
./configure --enable-optimizations --with-ensurepip=install
make -j$(nproc)
sudo make altinstall

# Verify installation
python3.12 --version
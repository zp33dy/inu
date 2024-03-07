FROM ubuntu:noble

FROM python:3.10.4

# Install pip
RUN python -m ensurepip

# Upgrade pip to the latest version
RUN python -m pip install --upgrade pip



# install firefox-esr for selenium
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    wget \
    firefox-esr \
    xz-utils

# manually install qalc since it is used by inu
RUN wget -O qalculate.tar.xz https://github.com/Qalculate/qalculate-gtk/releases/download/v4.5.1/qalculate-4.5.1-x86_64.tar.xz \
    && tar -xf qalculate.tar.xz \
    && rm qalculate.tar.xz \
    && mv qalculate-* qalculate \
    && cp qalculate/qalc /usr/bin/qalc

RUN useradd -ms /bin/bash inu

# Create and set permissions for /home/inu/app directory
# RUN mkdir /home/inu \
#     && chown -R inu:inu /home/inu
USER inu
WORKDIR /home/inu
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | bash -s -- -y
ENV PATH="/home/inu/.cargo/bin:${PATH}"

# # Get Rust
# RUN curl https://sh.rustup.rs -sSf | bash -s -- -y

# # ENV PATH="/root/.cargo/bin:${PATH}"

# Copy requirements and install dependencies
ADD requirements.txt requirements.txt
RUN pip install asyncpg matplotlib
RUN pip install -r requirements.txt
RUN pip install lavasnek-rs

# Copy application files
COPY . .

# Create qalculate config directory and copy config file
RUN mkdir -p .config/qalculate \
    && cp -r dependencies/conf/qalc.cfg .config/qalculate/qalc.cfg

USER root
# Create log directory and set permissions
RUN mkdir -p inu \
    && chown -R inu:inu inu
USER inu

CMD ["python3", "-O", "inu/main.py"]

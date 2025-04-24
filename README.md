# FrameWeaver

[![Tests & Push](https://github.com/TEConnectivity/FrameWeaver/actions/workflows/docker-build-push.yaml/badge.svg)](https://github.com/TEConnectivity/FrameWeaver/actions/workflows/docker-build-push.yaml)

**Still in developpement phase. Not suited for production !**

Process and decode fragmented LoRaWAN frames, receiving data over MQTT or HTTP, and publishing results to custom endpoints. 

Frameweaver is [configurale](/src/app/config.yaml).

## LNS

Each LNS got his specific format. Frameweaver cannot be compatible with every LNS on the market out of the box. The following LNS are compatible :

- TTN
- Loriot

## Input

The following input are available :

- MQTT : Listen from incoming MQTT messages from the specified Topic. Can be connected to a remote MQTT broker or the self-hosted one.


## Output

TODO

## Hosted MQTT Broker

If no MQTT Broker are available on the network, Frameweaver can host it. To make use of it, configure the MQTT input & output to `localhost` 

# Docker usage

An image is already available to be used, hosted on Github Container Registry :

    docker run -p 1883:1883 -p 8080:8080 ghcr.io/teconnectivity/frameweaver

## Build instructions

Assuming a Linux system, with `docker` command installed:

    cd src
    docker build -t frameweaver .

## Run instructions

Run with all default settings (default [config](/src/app/config.yaml)) :

    docker run -p 1883:1883 -p 8080:8080 frameweaver

Frameweaver can be also run with a custom config, by mounting it. Assuming your `custom_config.yaml` is inside your current working directory :

    docker run -v $(pwd)/custom_config.yaml:/app/app/config.yaml -p 1883:1883 -p 8080:8080 frameweaver


## Docker Compose

An example [docker-compose.yaml](/docker-compose.yml) is provided. A custom config can be easily used through volume : 

```
    volumes:
      - ./custom_config.yaml:/app/app/config.yaml
```


# Monitoring interface

A Web Interface is available to monitor which frames are pending for which devices : 

![monitor screenshot](images/monitor.png)

# Software architecture

![sw arch](images/arch.png)


# Sizing

For the docker deployment, container should have the following sizing :

- CPU : 1 Core
- RAM : 256 MB
- Network : 1 Mbps
- Disk space : No disk usage. Everything is stored in-memory

# Test

Tests dependencies are listed in the `requirements.txt` file under `tests` folder.
Tests should always be run inside the `tests` folder for proper initialization.


# Limitation

Stress tests shows the following :
    - At very high load (thousands of different devEUI over a minute) : 
      - Monitor interface can fail because the `frame_buffer` object is being rendered to front-end and modified in same time.
      - Self-hosted MQTT broker can crash (mosquitto process)
    - For a very high number of pending fragment (100k different devEUI) : Monitor interface can take up to 1 mn to fully load, because everything is displayed in the front-end.


# Roadmap

- HTTP Input/Output
- Do some modularization to allow interfacing multiple decoders
- Multi-stage docker to remove NPM dependencies (which add few hundreds of MB to the image size)
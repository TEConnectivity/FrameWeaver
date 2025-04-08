# FrameWeaver
**Still in developpement phase. Not suited for production !**

Process and decode fragmented LoRaWAN frames, receiving data over MQTT or HTTP, and publishing results to custom endpoints. 

Frameweaver is [configurale](/src/app/config.yaml).

## LNS

Each LNS got his specific format. Frameweaver cannot be compatible with every LNS on the market out of the box. The following LNS are compatible :

- TTN
- Loriot

## Input

The following input are avaiable :

- MQTT : Listen from incoming MQTT messages from the specified Topic. Can be connected to a remote MQTT broker or the self-hosted.


## Output

TODO

## Hosted MQTT Broker

If no MQTT Broker are available on the network, Frameweaver can host it. To make use of it, configure the MQTT input&output to `localhost` 

# Docker usage

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

# Roadmap

- HTTP Input/Output
- Tests
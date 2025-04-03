import os
from cerberus import Validator
import yaml

schema = {
    "input": {
        "type": "dict",
        "schema": {
            "mqtt": {
                "type": "dict",
                "schema": {
                    "enable": {"type": "boolean", "required": True},
                    "host": {"type": "string"},  # Host must have a port
                    "port": {"type": "integer", "min": 1, "max": 65535},
                    "topic": {"type": "string"},
                    "auth": {
                        "type": "dict",
                        "required": False,  # Optional
                        "schema": {
                            "username": {"type": "string","required": True},
                            "password": {"type": "string", "required": True},
                        },
                    },
                },
            },
            "http": {
                "type": "dict",
                "schema": {
                    "enable": {"type": "boolean", "required": True},
                    "host": {"type": "string"},
                    "port": {"type": "integer", "min": 1, "max": 65535},
                },
            },
        },
    },
    "output": {
        "type": "dict",
        "schema": {
            "mqtt": {
                "type": "dict",
                "schema": {
                    "enable": {"type": "boolean", "required": True},
                    "host": {"type": "string"},
                    "port": {"type": "integer", "min": 1, "max": 65535},
                    "topic": {"type": "string"},
                },
            },
            "http": {
                "type": "dict",
                "schema": {
                    "enable": {"type": "boolean", "required": True},
                    "url": {"type": "string"},
                },
            },
        },
    },
    "local-broker": {
        "type": "dict",
        "schema": {
            "enable": {"type": "boolean", "required": True},
        },
    },
    "frame": {
        "type": "dict",
        "schema": {
            "max_chunks": {"type": "integer", "min": 1, "required": True},
            "timeout": {"type": "integer", "min": 1, "required": True},
            "lns": {"type": "string", "allowed": ["ttn", "loriot"], "required": True},
        },
    },
    "log": {
        "type": "dict",
        "schema": {
            "level": {"type": "string", "allowed": ["debug", "info","warning","error","critical"], "required": True},
        },
    },
}

# Additional check: Ensure at least one input type is enabled
def check_input_enabled(config):
    input_section = config.get("input", {})
    mqtt_enabled = input_section.get("mqtt", {}).get("enable", False)
    http_enabled = input_section.get("http", {}).get("enable", False)
    
    return mqtt_enabled or http_enabled


# Load YAML
def load_yaml_config(filename):
    with open(filename, "r") as file:
        return yaml.safe_load(file)

# Validate YAML
def validate_config(config):
    validator = Validator(schema) # type: ignore
    
    if not validator.validate(config): # type: ignore
        print("❌ Config validation failed!")
        print(validator.errors) # type: ignore
        return False

    # Additional custom validation
    if not check_input_enabled(config):
        print("❌ Config validation failed! At least one input (MQTT or HTTP) must be enabled.")
        return False

    print("✅ Config is valid!")
    return True


def export_config():
    # Run validation
    if os.getenv("ENV") == "dev":
        config_file = "config_dev.yaml"
    else:
        config_file = "config.yaml"
    config = load_yaml_config(config_file)
    if validate_config(config) == False:
        raise Exception
    return config

if __name__ == "__main__":
    print(export_config())
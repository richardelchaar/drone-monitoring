import time
import random
from kafka import KafkaProducer
import json
from math import radians, sin, cos, sqrt, atan2
import threading

# Constants
takeoff_time = 10  # seconds
landing_time = 10  # seconds
cruise_speed = 22  # m/s
altitude_range = (380, 400)  # ft
battery_drain_takeoff = 2  # %
battery_drain_landing = 2  # %
cruise_battery_drain_per_second = 0.025  # %

# Coordinates
fulfillment_center = {"latitude": 43.5902, "longitude": -79.8250}  # Brampton, Canada
location_a = {"latitude": 43.7000, "longitude": -79.8000}  # Mississauga
location_b = {"latitude": 43.5000, "longitude": -79.9000}  # Oakville

def create_producer():
    for _ in range(10):  # Retry 10 times
        try:
            producer = KafkaProducer(
                bootstrap_servers=['kafka:9092'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            print("Connected to Kafka successfully.")
            return producer
        except Exception as e:
            print(f"Kafka not ready, retrying in 5 seconds... ({e})")
            time.sleep(5)
    raise Exception("Failed to connect to Kafka after 10 retries.")

producer = create_producer()

def haversine(coord1, coord2):
    """Calculate the great-circle distance between two points in meters."""
    R = 6371000  # Radius of Earth in meters
    lat1, lon1 = map(radians, [coord1['latitude'], coord1['longitude']])
    lat2, lon2 = map(radians, [coord2['latitude'], coord2['longitude']])

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def interpolate(coord1, coord2, speed, time_interval):
    """Interpolate the position based on speed and time."""
    distance = speed * time_interval  # Distance covered in meters
    total_distance = haversine(coord1, coord2)
    factor = distance / total_distance if total_distance > 0 else 0

    new_lat = coord1['latitude'] + factor * (coord2['latitude'] - coord1['latitude'])
    new_lon = coord1['longitude'] + factor * (coord2['longitude'] - coord1['longitude'])

    return {"latitude": new_lat, "longitude": new_lon}

def simulate_drone(drone_id, start, end, producer, topic="drone_telemetry"):
    """Simulate a drone flight from start to end and return."""
    battery_level = 100  # Start with full battery

    # Takeoff Phase
    for t in range(takeoff_time):
        altitude = 380 + 20 * (t / takeoff_time)  # Linear rise to 400 ft
        telemetry = {
            "drone_id": drone_id,
            "latitude": start["latitude"],
            "longitude": start["longitude"],
            "altitude": round(altitude, 2),
            "speed": 0,
            "battery_level": battery_level,
            "status": "Taking off",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
            "origin_latitude":start["latitude"],
            "origin_longitude": start["longitude"],
            "destination_latitude":end["latitude"],
            "destination_longitude": end["longitude"],
        }
        producer.send(topic, telemetry)
        time.sleep(1)
    battery_level -= battery_drain_takeoff

    # Cruise Phase
    current_position = start
    speed = 0
    while haversine(current_position, end) > 1:  # Stop when close to destination
        if speed < cruise_speed:
            speed += 2  # Accelerate by 2 m/s
        altitude = random.uniform(*altitude_range)  # Maintain random altitude
        current_position = interpolate(current_position, end, speed, 1)

        telemetry = {
            "drone_id": drone_id,
            "latitude": round(current_position["latitude"], 6),
            "longitude": round(current_position["longitude"], 6),
            "altitude": round(altitude, 2),
            "speed": speed,
            "battery_level": round(battery_level, 2),
            "status": "Cruising",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
            "origin_latitude":start["latitude"],
            "origin_longitude": start["longitude"],
            "destination_latitude":end["latitude"],
            "destination_longitude": end["longitude"],
        }
        producer.send(topic, telemetry)
        battery_level -= cruise_battery_drain_per_second
        time.sleep(1)

    # Landing Phase
    for t in range(landing_time):
        altitude = 400 - 400 * (t / landing_time)  # Linear descent to 0 ft
        telemetry = {
            "drone_id": drone_id,
            "latitude": end["latitude"],
            "longitude": end["longitude"],
            "altitude": round(altitude, 2),
            "speed": 0,
            "battery_level": battery_level,
            "status": "Landing",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
            "origin_latitude":start["latitude"],
            "origin_longitude": start["longitude"],
            "destination_latitude":end["latitude"],
            "destination_longitude": end["longitude"],
        }
        producer.send(topic, telemetry)
        time.sleep(1)
    battery_level -= battery_drain_landing

    # Return to Base
    simulate_drone(drone_id, end, start, producer, topic)



drone1_thread = threading.Thread(target=simulate_drone, args=("Drone1", fulfillment_center, location_a, producer))
drone2_thread = threading.Thread(target=simulate_drone, args=("Drone2", fulfillment_center, location_b, producer))

# Start Both Threads
drone1_thread.start()
drone2_thread.start()

# Wait for Both Threads to Finish
drone1_thread.join()
drone2_thread.join()

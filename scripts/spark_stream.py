from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, to_timestamp, lag, udf, collect_list
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType
from pyspark.sql.streaming.state import GroupState
import math

# Kafka Configuration
KAFKA_BROKER = "kafka:9092"  # Address of the Kafka broker
TOPIC_DRONE_TELEMETRY = "drone_telemetry"


# Define schema for drone telemetry
drone_telemetry_schema = StructType([
    StructField("timestamp", StringType(), True),
    StructField("drone_id", StringType(), True),
    StructField("latitude", DoubleType(), True),
    StructField("longitude", DoubleType(), True),
    StructField("origin_latitude", DoubleType(), True),
    StructField("origin_longitude", DoubleType(), True),
    StructField("destination_latitude", DoubleType(), True),
    StructField("destination_longitude", DoubleType(), True),
    StructField("altitude", DoubleType(), True),
    StructField("speed", DoubleType(), True),
    StructField("battery_level", DoubleType(), True),
    StructField("status", StringType(), True)
])






# Create Spark Session
spark = SparkSession.builder \
    .appName("DroneTelemetryStreaming") \
    .config("spark.cassandra.connection.host", "cassandra") \
    .master("spark://spark:7077") \
    .getOrCreate()




# Read streaming data from Kafka 'drone_telemetry' topic
drone_telemetry_stream = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", KAFKA_BROKER)
    .option("subscribe", TOPIC_DRONE_TELEMETRY)
    .option("startingOffsets", "latest")
    .load()
)

# Parse Kafka value column for drone telemetry data
drone_telemetry = drone_telemetry_stream.select(
    from_json(col("value").cast("string"), drone_telemetry_schema).alias("data")
).select("data.*")

# Convert 'timestamp' column to TIMESTAMP
drone_telemetry = drone_telemetry.withColumn(
    "timestamp", to_timestamp(col("timestamp"), "yyyy-MM-dd HH:mm:ss")
)



def haversine(lat1, lon1, lat2, lon2):
    R = 6371e3  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# Register the Haversine function as a UDF
haversine_udf = udf(haversine, DoubleType())


# Calculate distances
enriched_data = drone_telemetry.withColumn(
    "distance_from_origin",
    haversine_udf(
        col("latitude"), col("longitude"),
        col("origin_latitude"), col("origin_longitude")
    )
).withColumn(
    "distance_to_destination",
    haversine_udf(
        col("latitude"), col("longitude"),
        col("destination_latitude"), col("destination_longitude")
    )
)


final_data = enriched_data.select(
    "drone_id",
    "timestamp",
    "latitude",
    "longitude",
    "altitude",
    "speed",
    "battery_level",
    "status",
    "distance_from_origin",
    "distance_to_destination"
)



# Write enriched data with distances to Cassandra
final_data.writeStream \
    .format("org.apache.spark.sql.cassandra") \
    .options(table="drone_telemetry_with_distances", keyspace="drones") \
    .outputMode("append") \
    .option("checkpointLocation", "/tmp/drone_distance_checkpoint") \
    .start()


spark.streams.awaitAnyTermination()

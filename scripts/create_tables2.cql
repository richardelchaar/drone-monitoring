CREATE KEYSPACE IF NOT EXISTS drones
    WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};


USE drones;

CREATE TABLE IF NOT EXISTS drone_telemetry_with_distances (
                                                              drone_id TEXT,
                                                              timestamp TIMESTAMP,
                                                              latitude DOUBLE,
                                                              longitude DOUBLE,
                                                              altitude DOUBLE,
                                                              speed DOUBLE,
                                                              battery_level DOUBLE,
                                                              status TEXT,
                                                              distance_from_origin DOUBLE,
                                                              distance_to_destination DOUBLE,
                                                              PRIMARY KEY (drone_id, timestamp)  -- Partition by drone_id, cluster by timestamp
) WITH CLUSTERING ORDER BY (timestamp DESC);


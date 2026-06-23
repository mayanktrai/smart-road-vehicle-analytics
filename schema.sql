-- Smart Road Vehicle Analytics — database schema
-- Run: mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS road_analytics
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE road_analytics;

-- Every confirmed vehicle detection (one row per tracked vehicle).
CREATE TABLE IF NOT EXISTS vehicles (
    id            INT(11)      NOT NULL AUTO_INCREMENT,
    track_id      INT(11)      NULL,                 -- ByteTrack id within a run
    category      VARCHAR(50)  NOT NULL,             -- LMV / HMV / Two-Wheeler
    yolo_class    VARCHAR(50)  NULL,                 -- car / bus / truck / motorcycle ...
    confidence    FLOAT        NULL,
    detected_time TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_vehicles_time (detected_time),
    KEY idx_vehicles_category (category)
) ENGINE=InnoDB;

-- Speed violations linked back to the detected vehicle.
CREATE TABLE IF NOT EXISTS speed_violations (
    violation_id  INT(11)      NOT NULL AUTO_INCREMENT,
    vehicle_id    INT(11)      NOT NULL,
    logged_speed  FLOAT        NOT NULL,             -- km/h
    speed_limit   FLOAT        NULL,                 -- km/h in force for the lane
    violated_time TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (violation_id),
    KEY idx_violation_vehicle (vehicle_id),
    KEY idx_violation_time (violated_time),
    CONSTRAINT fk_violation_vehicle
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

-- ANPR results (slide 7: "ANPR letters, timestamps, and confidence scores").
CREATE TABLE IF NOT EXISTS anpr_logs (
    anpr_id       INT(11)      NOT NULL AUTO_INCREMENT,
    vehicle_id    INT(11)      NULL,
    plate_text    VARCHAR(20)  NOT NULL,
    confidence    FLOAT        NULL,
    read_time     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (anpr_id),
    KEY idx_anpr_plate (plate_text),
    KEY idx_anpr_time (read_time),
    CONSTRAINT fk_anpr_vehicle
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
        ON DELETE SET NULL
) ENGINE=InnoDB;

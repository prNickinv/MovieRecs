CREATE DATABASE IF NOT EXISTS default;

-- ratings.dat: UserID::MovieID::Rating::Timestamp
CREATE TABLE IF NOT EXISTS interactions (
    user_id UInt32,
    movie_id UInt32,
    rating UInt8,
    timestamp DateTime
) ENGINE = MergeTree()
ORDER BY (user_id, timestamp); 

-- Relational (MySQL) schema: normalised design
DROP TABLE IF EXISTS activity;
DROP TABLE IF EXISTS follows;
DROP TABLE IF EXISTS posts;
DROP TABLE IF EXISTS user_interests;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INT PRIMARY KEY,
    name VARCHAR(50),
    city VARCHAR(50),
    joined DATETIME
);

CREATE TABLE user_interests (
    user_id INT,
    interest VARCHAR(30),
    PRIMARY KEY (user_id, interest),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE follows (
    follower_id INT,
    followee_id INT,
    PRIMARY KEY (follower_id, followee_id),
    INDEX idx_followee (followee_id),
    FOREIGN KEY (follower_id) REFERENCES users(id),
    FOREIGN KEY (followee_id) REFERENCES users(id)
);

CREATE TABLE posts (
    id INT PRIMARY KEY,
    author_id INT,
    topic VARCHAR(30),
    text VARCHAR(200),
    likes INT,
    created DATETIME,
    INDEX idx_topic_likes (topic, likes),
    FOREIGN KEY (author_id) REFERENCES users(id)
);

CREATE TABLE activity (
    user_id INT,
    ts DATETIME,
    post_id INT,
    topic VARCHAR(30),
    action VARCHAR(10),
    INDEX idx_user_ts (user_id, ts)
);

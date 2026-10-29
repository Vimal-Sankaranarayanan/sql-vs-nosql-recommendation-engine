-- Q1: Friend suggestions for user 1 (friends of friends)
SELECT f2.followee_id AS suggested_user, COUNT(DISTINCT f1.followee_id) AS mutual_friends
FROM follows f1
JOIN follows f2 ON f2.follower_id = f1.followee_id
WHERE f1.follower_id = 1
  AND f2.followee_id <> 1
  AND f2.followee_id NOT IN (SELECT followee_id FROM follows WHERE follower_id = 1)
GROUP BY f2.followee_id
ORDER BY mutual_friends DESC
LIMIT 5;

-- Q2: Content recommendations for user 1 (top 2 topics from activity, best posts in them)
SELECT p.id, p.topic, p.likes
FROM posts p
JOIN (SELECT topic FROM activity WHERE user_id = 1 GROUP BY topic ORDER BY COUNT(*) DESC LIMIT 2) t
  ON t.topic = p.topic
WHERE p.author_id <> 1
ORDER BY p.likes DESC
LIMIT 5;

-- Q3: Trending topics
SELECT topic, SUM(likes) AS total_likes, COUNT(*) AS posts
FROM posts
GROUP BY topic
ORDER BY total_likes DESC
LIMIT 5;

-- Q4: Cold start - most followed users sharing a new user's interests (tech, music)
SELECT u.id, u.name, COUNT(DISTINCT f.follower_id) AS followers
FROM users u
JOIN user_interests ui ON ui.user_id = u.id AND ui.interest IN ('tech', 'music')
LEFT JOIN follows f ON f.followee_id = u.id
GROUP BY u.id, u.name
ORDER BY followers DESC
LIMIT 5;

-- Q5: Three-hop reach of user 1 (shows why deep JOINs get expensive)
SELECT COUNT(DISTINCT f3.followee_id) AS reachable_in_3_hops
FROM follows f1
JOIN follows f2 ON f2.follower_id = f1.followee_id
JOIN follows f3 ON f3.follower_id = f2.followee_id
WHERE f1.follower_id = 1;

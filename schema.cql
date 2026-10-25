CREATE KEYSPACE IF NOT EXISTS social_media_db
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

CREATE TABLE IF NOT EXISTS social_media_db.social_posts (
  post_id text PRIMARY KEY,
  platform text,
  sentiment text,
  topic text,
  content text
);

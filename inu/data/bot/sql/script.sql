CREATE TABLE IF NOT EXISTS guilds (
    guild_id BIGINT NOT NULL PRIMARY KEY,
    prefixes TEXT [] DEFAULT '{"%s"}'
);

CREATE TABLE IF NOT EXISTS music_history (
    guild_id BIGINT NOT NULL PRIMARY KEY,
    history JSONB
);

CREATE TABLE IF NOT EXISTS reddit_channels (
    guild_id BIGINT NOT NULL PRIMARY KEY,
    channel_ids BIGINT [],
    top_channel_ids BIGINT []
);

CREATE TABLE IF NOT EXISTS stats (
    guild_id BIGINT NOT NULL PRIMARY KEY,
    cmd_json JSONB
);

CREATE TABLE IF NOT EXISTS reminders (
    reminder_id int GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    remind_time TIMESTAMP,
    remind_text TEXT,
    channel_id BIGINT,
    creator_id BIGINT,
    message_id BIGINT
);

CREATE TABLE IF NOT EXISTS guild_timezones (
    guild_or_author_id BIGINT NOT NULL PRIMARY KEY,
    offset_hours INT
);

CREATE TABLE IF NOT EXISTS bot (
    "key" TEXT NOT NULL PRIMARY KEY,
    "value" TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tags (
    tag_id int GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    tag_key TEXT,
    tag_value TEXT,
    author_ids BIGINT [] NOT NULL,
    guild_ids BIGINT [],
    aliases TEXT []

);
-- supposed to work as cache, to prevent too many requests 429
CREATE TABLE IF NOT EXISTS myanimelist (
    mal_id BIGINT NOT NULL PRIMARY KEY,
    title TEXT,
    title_english TEXT,
    title_japanese TEXT,
    title_synonyms TEXT [],
    synopsis TEXT,
    background TEXT,
    related JSONB,
    genres JSONB [],
    "type" TEXT,
    episodes INT,
    ending_themes TEXT [],
    opening_themes TEXT [],
    duration INT,
    rating TEXT,
    "rank" INT,
    score FLOAT,
    popularity INT,
    source TEXT,
    "status" TEXT,
    airing_start TIMESTAMP,
    airing_stop TIMESTAMP,
    image_url VARCHAR(2048),
    studios JSONB [],
    cached_until TIMESTAMP,
    statistics JSONB,
    recommendations JSONB []
);
CREATE TABLE IF NOT EXISTS math_scores (
    guild_id BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    stage VARCHAR(50) NOT NULL,
    highscore INTEGER NOT NULL,
    "date" TIMESTAMP NOT NULL,
    PRIMARY KEY (guild_id, "user_id", stage)
);

CREATE TABLE IF NOT EXISTS polls (
    poll_id int GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    creator_id BIGINT NOT NULL,
    title VARCHAR(255),
    "description" VARCHAR(2048),
    options JSONB,
    polls JSONB,
    active_until TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS game_categories (
    guild_id BIGINT NOT NULL,
    category_id BIGINT NOT NULL,
    PRIMARY KEY (guild_id)
);

CREATE TABLE IF NOT EXISTS recent_games (
    guild_id BIGINT NOT NULL,
    game VARCHAR(100),
    timestamp TIMESTAMP,
    PRIMARY KEY (guild_id, game, timestamp)
);

CREATE EXTENSION IF NOT EXISTS pg_trgm;
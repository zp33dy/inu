CREATE TABLE IF NOT EXISTS guilds (
    guild_id BIGINT NOT NULL PRIMARY KEY,
    prefixes TEXT [] DEFAULT '{"%s"}',
    activity_tracking BOOLEAN NOT NULL DEFAULT FALSE,
    activity_tracking_duration INTERVAL NOT NULL DEFAULT '90 days'::INTERVAL
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
    tag_value TEXT[],
    author_ids BIGINT [] NOT NULL,
    guild_ids BIGINT [],
    aliases TEXT [],
    last_use TIMESTAMP NOT NULL

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


CREATE TABLE IF NOT EXISTS current_games (
    guild_id BIGINT NOT NULL,
    game VARCHAR(100),
    user_amount BIGINT NOT NULL,
    timestamp TIMESTAMP,
    PRIMARY KEY (guild_id, game, timestamp)
);

CREATE TABLE IF NOT EXISTS polls (
    poll_id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    creator_id BIGINT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description VARCHAR(2048),
    starts TIMESTAMP,
    expires TIMESTAMP NOT NULL,
    "anonymous" BOOLEAN NOT NULL,
    poll_type INTEGER NOT NULL,
    CONSTRAINT unique_message_id UNIQUE(message_id)
);

CREATE TABLE IF NOT EXISTS poll_votes (
    poll_id BIGINT NOT NULL 
        REFERENCES polls(poll_id) 
        ON DELETE CASCADE,
    option_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    PRIMARY KEY (poll_id, option_id, user_id)
);

CREATE TABLE IF NOT EXISTS poll_options (
    option_id SERIAL PRIMARY KEY,
    poll_id BIGINT NOT NULL 
        REFERENCES polls (poll_id)
        ON DELETE CASCADE,
    "reaction" VARCHAR(50) NOT NULL,
    "description" VARCHAR(255)
);


CREATE SCHEMA IF NOT EXISTS board;

CREATE TABLE IF NOT EXISTS board.boards (
    guild_id BIGINT,
    channel_id BIGINT NOT NULL,
    entry_lifetime INTERVAL,
    emoji TEXT,
    "enabled" BOOLEAN DEFAULT 'true'::BOOLEAN,
    PRIMARY KEY (guild_id, emoji)
);

-- tracks a message once
CREATE TABLE IF NOT EXISTS board.entries (
    message_id BIGINT NOT NULL,  -- original message
    board_message_id BIGINT,
    channel_id BIGINT NOT NULL,  -- original message
    content VARCHAR(4100),
    author_id BIGINT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    guild_id BIGINT NOT NULL,
    emoji TEXT NOT NULL,
    attachment_urls VARCHAR(2048)[],
    CONSTRAINT fk_unique_guild_emoji  -- when board deleted, delete all entries with it
        FOREIGN KEY (guild_id, emoji)
        REFERENCES board.boards(guild_id, emoji)
        ON DELETE CASCADE,
    PRIMARY KEY (message_id, emoji)
);

-- tracks who reacted to an entry
CREATE TABLE IF NOT EXISTS board.reactions (
    message_id BIGINT,  -- original message id
    reacter_id BIGINT,
    emoji TEXT,
    CONSTRAINT fk_emoji_message
        FOREIGN KEY (message_id, emoji)
        REFERENCES board.entries(message_id, emoji)
        ON DELETE CASCADE,
    PRIMARY KEY (message_id, reacter_id, emoji)
);

CREATE TABLE IF NOT EXISTS facts (
    facts_id SERIAL PRIMARY KEY,
    "type" TEXT,
    fact TEXT,
    sha256 TEXT UNIQUE  -- ensure, that facts won't be added multiple times 
);


CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE OR REPLACE FUNCTION ts_round( timestamptz, INT4 ) RETURNS TIMESTAMPTZ AS $$
    SELECT 'epoch'::timestamptz + '1 second'::INTERVAL * ( $2 * ( extract( epoch FROM $1 )::INT4 / $2 ) );
$$ LANGUAGE SQL;
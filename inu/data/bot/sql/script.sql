CREATE TABLE IF NOT EXISTS guilds (
    guild_id BIGINT NOT NULL PRIMARY KEY,
    prefixes TEXT [] DEFAULT '{"%s"}'
);
CREATE TABLE IF NOT EXISTS tags (
    tag_id int GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    tag_key TEXT,
    tag_value TEXT [],
    creator_id BIGINT NOT NULL,
    guild_id BIGINT
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
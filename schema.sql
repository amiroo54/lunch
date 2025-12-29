CREATE TABLE IF NOT EXISTS Users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    display_name TEST NOT NULL,
    password TEXT NOT NULL,
    active INTEGER DEFAULT 0 NOT NULL,
    role TEXT CHECK(role in ('archadmin', 'admin', 'user')) NOT NULL
);

CREATE TABLE IF NOT EXISTS Users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    display_name TEST NOT NULL,
    password TEXT NOT NULL,
    active INTEGER DEFAULT 0 NOT NULL,
    role TEXT CHECK(role in ('archadmin', 'admin', 'user')) NOT NULL
);

CREATE TABLE IF NOT EXISTS lunch_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_date TEXT NOT NULL UNIQUE,
    payer_id INTEGER,
    FOREIGN KEY (payer_id) REFERENCES Users(id)
);

CREATE TABLE IF NOT EXISTS lunch_attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lunch_event_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    FOREIGN KEY (lunch_event_id) REFERENCES lunch_events(id),
    FOREIGN KEY (user_id) REFERENCES Users(id),
    UNIQUE(lunch_event_id, user_id)
);

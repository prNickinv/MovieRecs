-- movies.dat: MovieID::Title::Genres
CREATE TABLE IF NOT EXISTS movies (
    movie_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    genres TEXT
);

-- users.dat: UserID::Gender::Age::Occupation::Zip-code
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    gender CHAR(1),
    age INTEGER,
    occupation INTEGER,
    zip_code TEXT
);

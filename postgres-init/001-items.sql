CREATE TABLE IF NOT EXISTS items (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  description TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO items (name, description, created_at)
VALUES
  ('Apple', 'FastAPI sample item from PostgreSQL', '2026-01-01T00:00:00Z'),
  ('Banana', 'Data from PostgreSQL table', '2026-01-01T00:00:00Z')
ON CONFLICT (name) DO NOTHING;

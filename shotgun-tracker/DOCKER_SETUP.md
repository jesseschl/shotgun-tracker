# Shotgun Tracker - Docker PostgreSQL Setup

## Getting Started

### Prerequisites
- Docker Desktop installed and running on your machine

### Setup Steps

1. **Copy the environment file:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your desired configuration (update `USERS_JSON` with your actual users and credentials).

2. **Start PostgreSQL:**
   ```bash
   docker-compose up -d
   ```
   This will start PostgreSQL in the background. The `-d` flag runs it as a daemon.

3. **Verify PostgreSQL is running:**
   ```bash
   docker-compose ps
   ```
   You should see `shotgun-tracker-db` with status "healthy" after 10-15 seconds.

4. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the Flask app:**
   ```bash
   python app.py
   ```
   The database tables will be initialized automatically on first run.

### Useful Docker Commands

- **Stop the database:**
  ```bash
  docker-compose down
  ```

- **View database logs:**
  ```bash
  docker-compose logs postgres
  ```

- **Access PostgreSQL CLI (psql):**
  ```bash
  docker exec -it shotgun-tracker-db psql -U postgres -d shotgun_tracker
  ```

- **Remove the database volume (warning: deletes all data):**
  ```bash
  docker-compose down -v
  ```

### Database Configuration

The docker-compose.yml is configured with:
- **Username:** postgres
- **Password:** password
- **Port:** 5432
- **Database name:** shotgun_tracker
- **Data persistence:** Yes (stored in Docker volume)

If you change the database credentials, update the `DATABASE_URL` in your `.env` file to match.

## Troubleshooting

- **Port 5432 already in use:** Another database is running. Either stop it or change the port in `docker-compose.yml` (e.g., `"5433:5432"`) and update your `DATABASE_URL`.
- **Connection refused:** Wait 10-15 seconds for PostgreSQL to fully start. Check `docker-compose logs postgres`.
- **Tables not created:** Ensure your `.env` file is in the project root and run `python app.py` once to initialize the database.

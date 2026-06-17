# Carbon Emissions Reporting Platform - Setup Guide

This guide will help you set up and run the Carbon Emissions Reporting Platform locally on your machine.

## Prerequisites

Before you begin, ensure you have the following installed on your system:

### Option 1: Docker (Recommended)
- [Docker Desktop](https://www.docker.com/products/docker-desktop) (includes Docker Engine and Docker Compose)

### Option 2: Local Python Development
- Python 3.9 or higher
- pip (Python package manager)
- A terminal/command prompt

## Project Structure

```
Carbon_Emissions_Reporting_Platform-main/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entry point
│   │   ├── models.py            # SQLAlchemy database models
│   │   ├── seed_data.py         # Initial database seed data
│   │   └── schemas.py           # Pydantic request/response schemas
│   ├── requirements.txt          # Python dependencies
│   ├── Dockerfile               # Backend container configuration
│   └── README.md
├── frontend/
│   ├── index.html               # Main dashboard UI
│   ├── script.js                # JavaScript frontend logic
│   ├── style.css                # Modern styling
│   ├── Dockerfile               # Frontend container configuration
│   └── README.md
├── docker-compose.yml           # Multi-container orchestration
├── README.md                    # Project overview
└── SETUP.md                     # This file
```

## Option 1: Running with Docker Compose (Recommended)

Docker Compose is the easiest way to get the entire stack running with minimal configuration.

### Step 1: Verify Docker Installation

```bash
docker --version
docker compose --version
```

Both commands should display version information.

### Step 2: Clone or Navigate to Project

```bash
cd /path/to/Carbon_Emissions_Reporting_Platform-main
```

### Step 3: Build and Start Containers

From the project root directory, run:

```bash
docker compose up --build
```

This command will:
- Build the backend image
- Build the frontend image
- Start both containers
- Initialize the SQLite database with seed data

### Step 4: Access the Application

**Frontend Dashboard:**
- URL: `http://localhost:3000`
- This is the main user interface where you submit emissions and view analytics

**Backend API Documentation:**
- URL: `http://localhost:8000/docs`
- Interactive Swagger UI to test API endpoints
- Includes request/response examples

**Backend Health Check:**
- URL: `http://localhost:8000/health`
- Returns `{"status": "ok"}` if the backend is running

### Step 5: Stop the Application

To stop the running containers:

```bash
docker compose down
```

This will:
- Stop all containers
- Remove container instances (but keep images)
- Keep the SQLite database intact

---

## Option 2: Running Locally Without Docker

This approach runs the backend and frontend on your local machine using Python.

### Prerequisites

- Python 3.9+
- pip (usually comes with Python)

### Step 1: Navigate to Project Root

```bash
cd /path/to/Carbon_Emissions_Reporting_Platform-main
```

### Step 2: Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This installs:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `sqlalchemy` - ORM for database
- `pydantic` - Data validation

### Step 3: Start the Backend Server

From the `backend/` directory:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started server process [12345]
```

The `--reload` flag enables hot-reloading for development. Keep this terminal open.

### Step 4: Start the Frontend Server

Open a **new terminal** and navigate to the frontend directory:

```bash
cd /path/to/Carbon_Emissions_Reporting_Platform-main/frontend
python -m http.server 3000
```

**Expected output:**
```
Serving HTTP on 0.0.0.0 port 3000 (http://0.0.0.0:3000/) ...
```

Keep this terminal open as well.

### Step 5: Access the Application

**Frontend Dashboard:**
- URL: `http://127.0.0.1:3000`

**Backend API Docs:**
- URL: `http://127.0.0.1:8000/docs`

**Backend Health Check:**
- URL: `http://127.0.0.1:8000/health`

### Step 6: Stop the Application

- **Backend**: Press `CTRL+C` in the backend terminal
- **Frontend**: Press `CTRL+C` in the frontend terminal

---

## Key Features to Test

Once the application is running, try these features:

### 1. Submit an Emission Record
- Go to "Record Emissions" form
- Select a Scope (1 or 2)
- Choose an Activity (e.g., Diesel, Grid Electricity)
- Category and Unit auto-populate based on historical data
- Enter Quantity and Date
- Click "Record Emission"
- Check the "Recent Records" table below

### 2. Submit Business Metric
- Go to "Business Metrics" form
- Enter or modify the metric name (default: "Tons of Steel Produced")
- Adjust unit and value
- Click "Save Metric"
- Watch the "Emission Intensity" KPI card update

### 3. View Analytics Dashboards
- **YoY Emissions Chart**: Stacked bar chart comparing Scope 1 and 2 across years
- **Hotspots Chart**: Doughnut chart showing top-contributing activities
- **Monthly Trend**: Line chart showing emission patterns throughout the year

### 4. Test Audit Trail
- Submit an emission record
- The audit log (if any manual overrides exist) appears in the "Audit Trail" panel
- Each entry shows timestamp, old/new values, and reason

---

## Database

The application uses **SQLite** for simplicity.

**Database file location:**
- Docker: Inside the container (persistent with docker volumes)
- Local: `backend/emissions.db` (created on first run)

**To reset the database:**
- **Docker**: `docker compose down -v` (removes volumes)
- **Local**: Delete `backend/emissions.db` and restart the backend

The database auto-initializes with seed data on startup, including:
- Versioned emission factors for 2024, 2025, 2026
- Sample emission records
- Sample business metrics

---

## Troubleshooting

### "Port 3000 is already in use"

Use an alternative port:
```bash
python -m http.server 5500
```
Then access at `http://127.0.0.1:5500`

### "Port 8000 is already in use"

Find and stop the process using port 8000, or run the backend on a different port:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```
Then update the frontend's API_BASE in `script.js` if needed.

### "ModuleNotFoundError: No module named 'fastapi'"

Ensure you've installed dependencies:
```bash
cd backend
pip install -r requirements.txt
```

### "Connection refused" when accessing frontend

Ensure:
1. Backend is running on `http://0.0.0.0:8000`
2. Frontend is accessing `http://127.0.0.1:8000` (check `script.js`)
3. Both servers are in separate terminals

### Docker container exits immediately

Check logs:
```bash
docker compose logs backend
docker compose logs frontend
```

### Changes not reflecting in browser

- **Backend**: Should auto-reload with `--reload` flag
- **Frontend**: Hard refresh browser (`Ctrl+Shift+R` or `Cmd+Shift+R`)
- **Docker**: Rebuild with `docker compose up --build`

---

## Environment Variables

Currently, the application uses sensible defaults and doesn't require environment configuration.

**Optional customization in `backend/app/main.py`:**
- Change database file location
- Modify API port
- Add CORS origins

---

## API Endpoints

### Emissions
- `GET /emissions` - List all emission records
- `POST /emissions` - Create new emission record
- `POST /emissions/{record_id}/override` - Override emission value

### Business Metrics
- `GET /business-metrics` - List all business metrics
- `POST /business-metrics` - Create new business metric

### Analytics
- `GET /analytics/yoy-emissions?year=2026` - Year-over-year comparison
- `GET /analytics/emission-intensity?metric_name=...` - Intensity calculation
- `GET /analytics/hotspots` - Top emission sources
- `GET /analytics/monthly-emissions?year=2026` - Monthly breakdown

### Master Data
- `GET /master-data/activity-options` - Available activities and factors

See `http://localhost:8000/docs` for interactive API documentation.

---

## Next Steps

1. **Explore the Codebase**
   - `backend/app/main.py` - API endpoints
   - `backend/app/models.py` - Database schema
   - `frontend/script.js` - Frontend logic

2. **Customize Seed Data**
   - Edit `backend/app/seed_data.py` to add your own emission factors

3. **Extend Features**
   - Add Scope 3 emissions
   - Implement user authentication
   - Add more analytics dashboards

4. **Deploy to Production**
   - Use Docker image for cloud deployment
   - Set up PostgreSQL for production database
   - Configure environment variables for security

---

## Support

For issues or questions:
- Check API docs at `http://localhost:8000/docs`
- Review backend logs in terminal
- Check browser console for frontend errors
- Consult README.md for architectural details

Happy forecasting! 🌍

# AI Employee Productivity Monitoring System

A scalable, clean architecture full-stack application designed to track computer activity levels, application focus times, and webcam-based attention metrics (detecting distractions, gaze deviations, absence, and drowsiness in real time).

---

## Technical Stack & Abstractions
- **Frontend Panel**: React 18 dashboard styled with premium Tailwind CSS. Connects to backend endpoints and subscribes to real-time WebSockets to display instant camera alerts.
- **Backend Service**: FastAPI (Python) hosting REST endpoints, SQLAlchemy data layer mapping, and multithreaded WebSocket broadcast managers.
- **Database Storage**: SQLite database (`database/employee_monitoring.db`) tracking logs history and user preferences.
- **AI Core Engine**: Python service coordinating OpenCV cameras, YOLOv11 distraction detection, and Google MediaPipe eye and posture landmark trackers.
- **Desktop Tracker App**: Electron client wrapper managing clock-in UI prompts, terminal logging status feeds, and local process controls.

---

## Folder Architecture

```text
EMPLOYEE/
├── database/                    # SQLite schemas creation
│   └── build_db.py              # Schema migration & mock data seeding
├── backend/                     # FastAPI back-end API application
│   ├── app/                      
│   │   ├── core/                # DB clients, Security hashing, config loaders
│   │   ├── models/              # SQLAlchemy model structures
│   │   ├── schemas/             # Pydantic validation scopes
│   │   ├── api/                 # Auth, Activity, Logs, Websocket endpoints
│   │   └── services/            # JWT authentication & websocket managers
│   └── main.py                  # API service entry runner
├── ai_engine/                   # OpenCV + YOLO + MediaPipe tracking daemon
│   ├── detectors/               # Object and landmark detection loops
│   ├── utils/                   # Video Capture grabbers (with canvas mockups)
│   └── engine.py                # Scanner loop coordinating socket logging
├── desktop/                     # Electron clock-in GUI utility
│   ├── main.js                  # IPC handlers and runner configurations
│   ├── preload.js               # IPC windows bridging
│   └── index.html               # Glassmorphic local dashboard control
└── frontend/                    # Vite + React Admin Dashboard
    ├── src/
    │   ├── components/          # Glassmorphic containers, Sidebar,Alerts lists
    │   ├── pages/               # Login, Overview Registry tables, configurations
    │   └── utils/               # Fetch API wrappers
    └── tailwind.config.js       # Premium dark mode themes mapping
```

---

## Quick Setup & Running Guide

### 1. Database Setup
Ensure Python is installed and run the compiler script to create and populate the SQLite database:
```bash
python database/build_db.py
```
This generates `database/employee_monitoring.db` with preprocessed hashes credentials (User: `admin` / Password: `Password123` ; User: `alice` / Password: `Password123`).

### 2. Launch FastAPI Backend
Navigate to the `backend/` directory, install packages, and start the development server:
```bash
cd backend
pip install -r requirements.txt
python main.py
```
*API docs will be available at [http://localhost:8000/docs](http://localhost:8000/docs).*

### 3. Run Web Dashboard
Navigate to the `frontend/` directory, configure packages, and start Vite:
```bash
cd frontend
npm install
npm run dev
```
*Open [http://localhost:5173](http://localhost:5173) in your browser and login as `admin` / `Password123` to watch incoming streams.*

### 4. Start AI Scanner Engine (Standalone Mode)
You can run the camera detector in standalone offline mode:
```bash
cd ai_engine
pip install -r requirements.txt
python engine.py alice
```
If the backend is running, the script logs into the system, creates WebSocket streams, and registers cell phone/gaze alerts in real-time. If the backend is off, it auto-detects offline status and executes local diagnostics.

### 5. Spawn Desktop Agent (Electron Portal)
Configure parameters and launch the Electron application:
```bash
cd desktop
npm install
npm start
```
The desktop app allows the user to click **Clock In**, which automatically spawns `ai_engine/engine.py` as a child process and pipes its console feedback directly into the local GUI console!

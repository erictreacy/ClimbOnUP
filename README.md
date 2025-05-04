# UP Michigan Climbing Data App

An interactive web application that displays climbing areas in Michigan's Upper Peninsula, using data from Mountain Project.

## Project Structure

```
ClimbOnUP/
├── backend/
│   ├── src/
│   │   ├── scraper.py      # Mountain Project data scraper
│   │   └── requirements.txt # Python dependencies
│   └── package.json
├── frontend/
│   ├── public/
│   │   └── climbing_data.json # Scraped climbing data
│   ├── src/
│   │   ├── App.tsx        # Main application component
│   │   ├── index.css      # Global styles
│   │   └── main.tsx       # Application entry point
│   ├── package.json
│   └── .env               # Environment variables (Mapbox token)
└── package.json           # Root package.json for workspace management
```

## Features

- Scrapes climbing area data from Mountain Project
- Interactive map with area markers using Mapbox
- Sidebar listing of climbing areas
- Area details including grade range and route count
- SQLite database for data storage

## Setup

1. Install dependencies:
   ```bash
   npm run install:all
   ```

2. Set up environment variables:
   Create `frontend/.env` with your Mapbox token:
   ```
   VITE_MAPBOX_TOKEN=your_mapbox_token_here
   ```

3. Run the scraper:
   ```bash
   npm run start:backend
   ```

4. Start the frontend development server:
   ```bash
   npm run start:frontend
   ```

5. Open http://localhost:5173 in your browser

## Technologies Used

- Frontend:
  - React with TypeScript
  - Mapbox GL JS
  - Vite build tool
- Backend:
  - Python
  - BeautifulSoup4 for web scraping
  - SQLite for data storage

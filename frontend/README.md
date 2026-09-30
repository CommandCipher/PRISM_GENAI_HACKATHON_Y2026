# Smart Troubleshooter Frontend

React + Vite demo frontend for the Samsung PRISM Theme 2 Smart Guided Troubleshooting Engine.

## Run

Start the FastAPI backend first:

    cd backend
    uvicorn app.main:app --reload

Then:

    cd frontend
    npm install
    npm run dev

Open http://localhost:5173

The Vite development server proxies /api and /health to http://127.0.0.1:8000, so the frontend uses the real backend and does not contain mock troubleshooting data.

## Demo

Use:
- My touchscreen is not responding
- My screen is completely blank
- My phone is behaving weirdly

Run the same supported query twice without restarting the backend to demonstrate the semantic fast path and the metadata returned by the Device Brain.

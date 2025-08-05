# LineCook FastAPI Commands

# Start the FastAPI server
serve:
    uv run python main.py server

# Stop the FastAPI server
stop:
    pkill -f "python main.py server" || true
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Test the API endpoints
test:
    uv run python test_api.py

# Run the legacy CLI version
cli:
    uv run python main.py

# Install/sync dependencies
install:
    uv sync

# Open FastAPI documentation in browser
docs:
    @echo "Opening FastAPI docs at http://localhost:8000/docs"
    @if command -v open >/dev/null 2>&1; then open http://localhost:8000/docs; elif command -v xdg-open >/dev/null 2>&1; then xdg-open http://localhost:8000/docs; else echo "Could not detect browser opener. Please manually visit http://localhost:8000/docs"; fi

# Start the server with Docker Compose
docker-serve:
    docker compose up --build -d

# Stop the Docker server
docker-stop:
    docker compose down
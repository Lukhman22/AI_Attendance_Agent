# ---------- Build React ----------
    FROM node:22 AS frontend-builder

    WORKDIR /frontend
    
    COPY frontend/package*.json ./
    RUN npm install
    
    COPY frontend/ .
    RUN npm run build
    
    
    # ---------- Python Backend ----------
    FROM python:3.13-slim
    
    WORKDIR /app
    
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt
    
    COPY . .
    
    # Copy React build into the project
    COPY --from=frontend-builder /frontend/dist ./frontend/dist
    
    EXPOSE 8000
    
    CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
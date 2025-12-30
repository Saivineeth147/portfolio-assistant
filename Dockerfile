# Multi-stage build for Portfolio Assistant
# Stage 1: Build frontend
FROM node:18-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend
FROM python:3.10-slim

# Create non-root user for HuggingFace Spaces
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user
ENV PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Install Python dependencies
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy backend
COPY --chown=user backend/ ./backend/

# Copy frontend build
COPY --from=frontend-builder --chown=user /app/frontend/dist ./frontend/dist

# Expose port (HuggingFace uses 7860)
EXPOSE 7860
ENV PORT=7860

# Run server
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]

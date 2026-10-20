# One image for the whole app: the React frontend is built, then served by the FastAPI backend.
# Works as a Hugging Face Space (sdk: docker, port 7860) or anywhere Docker runs. Needs about 3 GB of RAM.

FROM node:22-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg espeak-ng && rm -rf /var/lib/apt/lists/*
WORKDIR /app/backend
# the pins GitHub Actions tests (including the real-model checks) before every deploy; CPU-only PyTorch keeps the image small
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt
COPY backend/ ./
COPY --from=frontend /frontend/dist /app/frontend/dist
# lexicons and models are fetched at build time so the first analysis does not wait for downloads
ENV HF_HOME=/app/hf
RUN python -m pg.kb.fetch && python -c "from pg.phones import PhoneModel; from pg.align import WordAligner; from pg.diarize import Diarizer; from huggingface_hub import snapshot_download; from pg.asr import ASR_MODEL; PhoneModel(); WordAligner(); Diarizer(); snapshot_download(ASR_MODEL, allow_patterns=['*.json', '*.txt', 'model.safetensors'])"
# Hugging Face runs the container as user 1000: let it write its caches (transcripts, speaker turns)
RUN mkdir -p /app/backend/data/cache && chmod -R a+rwX /app/backend/data /app/hf
# load the models in the background as soon as the server starts
ENV PG_WARM=1
EXPOSE 7860
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]

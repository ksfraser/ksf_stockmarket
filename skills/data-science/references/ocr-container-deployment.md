# OCR Container Deployment Notes

## Containerfile/Podfile

```dockerfile
FROM docker.io/python:3.11-slim
LABEL maintainer="KSF Development Team"
LABEL description="KSF Tesseract OCR REST API Service"
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt
COPY ocr_api.py /app/ocr_api.py
WORKDIR /app
EXPOSE 8100
CMD ["uvicorn", "ocr_api:app", "--host", "0.0.0.0", "--port", "8100"]
```

## Build and run

```bash
podman build -f Podfile -t ksf-tesseract .
podman run -d --name ksf-tesseract --restart unless-stopped -p 8100:8100 localhost/ksf-tesseract:latest
```

## Compose gotcha

`podman-compose 1.0.6` may throw `RuntimeError: volume [...] not defined in top level` if the compose file references volumes from another compose context. Workaround: build/run the OCR service directly, or use a separate compose file that defines its own volumes.

## Registry access fallback

Default ansible STT/TTS images (`docker.io/rhasspy/wyoming-faster-whisper`, `docker.io/rhasspy/wyoming-piper`) may return `requested access to the resource is denied` or `unauthorized` from restricted networks. In that case:

1. Check for locally cached images: `podman images | grep -iE "whisper|piper|rhasspy"`
2. Check alternative registries: `quay.io/rhasspy/...` (may also be blocked)
3. Build a local replacement container from `faster-whisper` + FastAPI, similar to the tesseract pattern.
4. For STT specifically, the local `faster-whisper` Python package is already present in the host environment; a lightweight wrapper API is sufficient.

## Health check

```bash
curl -s http://localhost:8100/health
# Expected: {"status":"ok"}
```

## Ansible roles found

- `/root/.ansible/roles/ksf.ocr`
- `/root/.ansible/roles/ksf.tts`
- `/root/.ansible/roles/ksf.stt`

Actual container start logic uses `podman run --pod ksfii-pod ...` with image defaults from role `defaults/main.yml`. If pull fails, override `container_image` in inventory/host_vars to a reachable registry mirror or local image name.

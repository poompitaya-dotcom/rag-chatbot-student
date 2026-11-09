# Example only: how this app would be packaged for production (Module 4).
# You won't build it in class. Read it top to bottom: each instruction
# adds a layer to the image, and the finished image runs the same way on
# any machine - your laptop, the CI runner, or a production server.

# Start from a small, pinned Python base image.
FROM python:3.11-slim

WORKDIR /app

# 1. Dependencies first. Docker caches each layer, so when only your code
#    changes, this slow step is reused instead of re-run.
#    CPU-only PyTorch keeps the image ~2 GB smaller than the default CUDA build.
COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt

# 2. Bake the model weights into the image. A production container should
#    never download 1 GB when it starts.
RUN python -c "from sentence_transformers import SentenceTransformer; \
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM; \
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); \
AutoTokenizer.from_pretrained('google/flan-t5-base'); \
AutoModelForSeq2SeqLM.from_pretrained('google/flan-t5-base')"

# 3. The application: code, prompts, policy and knowledge. Tests, logs and
#    your venv stay out (see .dockerignore).
COPY src/ src/
COPY prompts/ prompts/
COPY data/ data/
COPY app.py AGENT_POLICY.md ./

# 4. Build the knowledge base at build time, so every container from this
#    image answers from exactly the same, versioned index.
RUN python -m src.ingest

# 5. At runtime: no network needed for models, and Streamlit on port 8501.
#    Logs written inside a container vanish when it stops; a real deployment
#    sends them to a logging service or a mounted volume.
ENV HF_HUB_OFFLINE=1
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]

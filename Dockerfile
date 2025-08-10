FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip

# Instala todas las dependencias excepto torch (que da error)
RUN grep -v "torch" requirements.txt > requirements-no-torch.txt && pip install -r requirements-no-torch.txt

# Instala torch para CPU desde el repositorio oficial PyTorch
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

COPY . .

CMD ["python", "bot.py"]

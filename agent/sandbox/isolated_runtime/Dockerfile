FROM python:3.13-slim
RUN pip install --no-cache-dir docker==7.1.0 requests==2.32.5 pillow==12.0.0 pandas==2.3.3 matplotlib==3.10.7 pypdf==6.3.0 python-docx==1.2.0
COPY manager.py proxy.py driver.py collector.py /opt/codeexec/
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
CMD ["python", "/opt/codeexec/manager.py"]

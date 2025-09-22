FROM python:3.11-slim
WORKDIR /app
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
RUN pip install --no-cache-dir \
  streamlit==1.37.1 \
  pandas==2.2.2 \
  sqlalchemy==2.0.32 \
  pymysql==1.1.1 \
  python-dotenv==1.0.1 \
  openpyxl==3.1.5 \
  xlrd==2.0.1 \
  requests==2.32.3 \
  python-docx==1.1.2 \
  pypdf==4.3.1
COPY app.py .
EXPOSE 8501
CMD ["python","-m","streamlit","run","app.py","--server.port=8501","--server.address=0.0.0.0","--server.runOnSave=true"]

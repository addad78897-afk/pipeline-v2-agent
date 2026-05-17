# 管线V2.0 Agent — Docker 部署文件
# Railway 自动检测 Dockerfile 并构建
FROM python:3.11-slim

# 安装 Node.js（用于前端构建）
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean

WORKDIR /app

# 后端依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 前端依赖 + 构建
COPY frontend/package.json frontend/package-lock.json frontend/
RUN cd frontend && npm install

# 复制全部源码
COPY . .

# 构建前端
RUN cd frontend && npm run build

# 启动后端（托管前端静态文件）
EXPOSE 8000
CMD cd backend && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}

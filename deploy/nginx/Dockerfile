# 语法: docker/dockerfile:1.7
# 阶段 1: 构建前端
FROM node:20-alpine AS frontend-builder
WORKDIR /app
# 国内构建可传 --build-arg NPM_REGISTRY=https://registry.npmmirror.com
ARG NPM_REGISTRY=
RUN if [ -n "$NPM_REGISTRY" ]; then npm config set registry "$NPM_REGISTRY"; fi
# 先拷依赖清单利用缓存
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
# 再拷源码构建（.dockerignore 已排除 node_modules/dist）
COPY frontend/ .
RUN npm run build

# 阶段 2: nginx 托管静态 + 反代后端
FROM nginx:1.27-alpine
# 清默认配置
RUN rm /etc/nginx/conf.d/default.conf
# 拷 nginx 配置
COPY deploy/nginx/nginx.conf /etc/nginx/conf.d/default.conf
# 拷前端构建产物
COPY --from=frontend-builder /app/dist /usr/share/nginx/html
EXPOSE 80

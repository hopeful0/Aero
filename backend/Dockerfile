# uv 镜像默认拉 DockerHub（astral/uv）。国内可通过 --build-arg UV_IMAGE=... 替换为代理镜像
ARG UV_IMAGE=astral/uv:latest
FROM ${UV_IMAGE} AS uv

FROM python:3.12-slim

WORKDIR /app

COPY --from=uv /uv /usr/local/bin/uv

# 国内构建可传 --build-arg UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG UV_INDEX_URL=
ENV UV_INDEX_URL=${UV_INDEX_URL}

COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project

COPY . .
RUN uv sync --no-dev --frozen

EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# 第一阶段：构建wheel包
FROM python:3.11-slim AS builder

WORKDIR /build
COPY . .
RUN python -m pip install build && \
    python -m build

# 第二阶段：运行环境
FROM python:3.11-slim-bullseye

ENV DEBIAN_FRONTEND=noninteractive

# 复制字体文件
COPY ./data/fonts/sarasa-mono-sc-regular.ttf /usr/share/fonts/

# 安装系统依赖
RUN apt-get -yqq update && \
    apt-get -yqq install --no-install-recommends \
        wkhtmltopdf \
        ffmpeg \
        curl \
        jq \
        unzip && \
    apt-get -yq clean && \
    apt-get -yq purge --auto-remove -o APT::AutoRemove::RecommendsImportant=false && \
    rm -rf /var/lib/apt/lists/*

# 创建应用目录
WORKDIR /app

# 复制第一阶段构建的wheel包并安装
COPY --from=builder /build/dist/*.whl /app/

# 下载Web UI并安装依赖
RUN LATEST_RELEASE_URL=$(curl -s https://api.github.com/repos/DarkSkyTeam/chatgpt-for-bot-webui/releases | jq -r '.[0].assets[] | select(.name == "dist.zip") | .browser_download_url') \
    && curl -L -o dist.zip "$LATEST_RELEASE_URL" \
    && unzip dist.zip -d /tmp/web_dist \
    && rm dist.zip && \
    mkdir -p /app/web && \
    mv /tmp/web_dist/dist/* /app/web && \
    pip install --no-cache-dir *.whl && \
    pip cache purge && \
    python -c "from pycloudflared import try_cloudflare; try_cloudflare(-1)" || true && \
    rm *.whl

# 移除不再需要的包
RUN apt-get -yqq remove --purge curl jq unzip

# 复制应用代码
COPY ./docker/start.sh /app/docker/
COPY ./data /tmp/data
EXPOSE 8080

CMD ["/bin/bash", "/app/docker/start.sh"]

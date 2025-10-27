FROM pytorch/pytorch:2.2.1-cuda12.1-cudnn8-runtime

# ===== 仅供 git/pip 用的构建期代理（可通过 --build-arg 覆盖）=====
ARG HTTP_PROXY=http://172.17.0.1:7890
ARG HTTPS_PROXY=http://172.17.0.1:7890
ARG NO_PROXY=localhost,127.0.0.1,.local,registry-1.docker.io

# 让 git/pip 继承代理（APT 不用）
ENV http_proxy=${HTTP_PROXY} \
    https_proxy=${HTTPS_PROXY} \
    no_proxy=${NO_PROXY} \
    DEBIAN_FRONTEND=noninteractive \
    PIP_DEFAULT_TIMEOUT=600

# ===== APT 不走代理（临时清空 env），并强制 IPv4，安装基础包 =====
RUN set -eux; \
    rm -f /etc/apt/apt.conf.d/*proxy* || true; \
    env -u http_proxy -u https_proxy \
      apt-get update -o Acquire::ForceIPv4=true -o Acquire::Retries=5; \
    env -u http_proxy -u https_proxy \
      apt-get install -y --no-install-recommends \
        curl vim git build-essential coreutils ca-certificates; \
    update-ca-certificates; \
    rm -rf /var/lib/apt/lists/*

# ===== git 显式走代理（有些环境需要）=====
RUN git config --global http.proxy  "$http_proxy"  || true && \
    git config --global https.proxy "$https_proxy" || true

# ===== 拉取 qlib 指定版本（如外网不通，可改为 COPY 本地源码）=====
RUN git clone https://github.com/microsoft/qlib.git /workspace/qlib
WORKDIR /workspace/qlib
RUN git fetch && git reset 3e72593b8c985f01979bebcf646658002ac43b00 --hard

# ===== pip 环境与依赖（走代理）。可选：换国内源 =====
RUN python -m ensurepip --upgrade || true && \
    python -m pip install -U --retries 5 pip setuptools wheel && \
    python -m pip config set global.retries 5 && \
    python -m pip config set global.timeout 600
# 如需国内镜像，取消下一行注释
# RUN python -m pip config set global.index-url https://mirrors.aliyun.com/pypi/simple

# cython 有兼容性，固定一个稳定版本；再装 qlib & 依赖
RUN python -m pip install -U --retries 5 Cython==0.29.37
RUN python -m pip install -e .
RUN python -m pip install --no-cache-dir --retries 5 \
      catboost xgboost scipy==1.11.4 tables
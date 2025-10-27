FROM pytorch/pytorch:2.2.1-cuda12.1-cudnn8-runtime

# === 仅给 git/pip 用的代理（容器内不要用 127.0.0.1；改成你的宿主可达地址）===
ARG HTTP_PROXY=http://172.17.0.1:7890
ARG HTTPS_PROXY=http://172.17.0.1:7890
ARG NO_PROXY=localhost,127.0.0.1,.local,registry-1.docker.io

ENV http_proxy=${HTTP_PROXY} \
    https_proxy=${HTTPS_PROXY} \
    no_proxy=${NO_PROXY} \
    DEBIAN_FRONTEND=noninteractive \
    PIP_DEFAULT_TIMEOUT=600

# === APT 不走代理 ===
RUN set -eux; \
    rm -f /etc/apt/apt.conf.d/*proxy* || true; \
    env -u http_proxy -u https_proxy \
      apt-get update -o Acquire::ForceIPv4=true -o Acquire::Retries=5; \
    env -u http_proxy -u https_proxy \
      apt-get install -y --no-install-recommends \
        curl vim git build-essential coreutils ca-certificates; \
    update-ca-certificates; \
    rm -rf /var/lib/apt/lists/*

# === git 显式配置代理 + 提高超时阈值 ===
RUN git config --global http.proxy  "$http_proxy"  || true && \
    git config --global https.proxy "$https_proxy" || true && \
    git config --global http.lowSpeedLimit  1024  && \
    git config --global http.lowSpeedTime   120   && \
    git --version && git config -l | grep -E 'proxy|lowSpeed' || true

# === clone（带详细日志 + 多次重试）===
# 如果不需要完整历史，也可加 --depth=1 提高成功率
RUN set -eux; \
    for i in 1 2 3 4 5; do \
      echo ">>> [try $i] cloning qlib..." ; \
      GIT_CURL_VERBOSE=1 GIT_TRACE_PACKET=1 git clone https://github.com/microsoft/qlib.git /workspace/qlib && break; \
      echo ">>> clone failed, sleep 10s then retry..."; sleep 10; \
    done

WORKDIR /workspace/qlib
RUN git fetch && git reset 3e72593b8c985f01979bebcf646658002ac43b00 --hard

# === pip（走代理）===
RUN python -m ensurepip --upgrade || true && \
    python -m pip install -U --retries 5 pip setuptools wheel && \
    python -m pip config set global.retries 5 && \
    python -m pip config set global.timeout 600
# 可选：国内镜像
# RUN python -m pip config set global.index-url https://mirrors.aliyun.com/pypi/simple

RUN python -m pip install -U --retries 5 Cython==0.29.37
RUN python -m pip install -e .
RUN python -m pip install --no-cache-dir --retries 5 \
      catboost xgboost scipy==1.11.4 tables
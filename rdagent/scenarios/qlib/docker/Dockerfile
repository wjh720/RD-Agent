FROM pytorch/pytorch:2.2.1-cuda12.1-cudnn8-runtime

# ===== 构建期代理默认值（可被外部 --build-arg 覆盖）=====
ARG HTTP_PROXY=http://172.17.0.1:7890
ARG HTTPS_PROXY=http://172.17.0.1:7890
ARG NO_PROXY=localhost,127.0.0.1,.local,registry-1.docker.io

# 让构建期的每个步骤都继承代理（apt、pip、git 都会用）
ENV http_proxy=${HTTP_PROXY} \
    https_proxy=${HTTPS_PROXY} \
    no_proxy=${NO_PROXY} \
    DEBIAN_FRONTEND=noninteractive

# ===== APT 走代理 + 换国内源，提升稳定性 =====
RUN printf 'Acquire::http::Proxy "%s";\nAcquire::https::Proxy "%s";\n' "$http_proxy" "$https_proxy" \
    > /etc/apt/apt.conf.d/90proxy

RUN sed -i 's|http://archive.ubuntu.com/ubuntu/|http://mirrors.aliyun.com/ubuntu/|g; \
            s|http://security.ubuntu.com/ubuntu|http://mirrors.aliyun.com/ubuntu|g' \
    /etc/apt/sources.list

# ===== 安装基础依赖（每个 RUN 独立，避免命令串行出错）=====
RUN apt-get clean && apt-get update -o Acquire::Retries=5 && apt-get install -y --no-install-recommends \
      curl vim git build-essential coreutils ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# git 也显式配置代理（有些环境只认 git 自己的代理）
RUN git config --global http.proxy  "$http_proxy"  || true && \
    git config --global https.proxy "$https_proxy" || true

# ===== 拉 qlib 指定版本 =====
RUN git clone https://github.com/microsoft/qlib.git
WORKDIR /workspace/qlib
RUN git fetch && git reset 3e72593b8c985f01979bebcf646658002ac43b00 --hard

# ===== pip 加强：升级工具 + 设置超时/重试（可选：换源）=====
RUN python -m ensurepip --upgrade || true && \
    python -m pip install -U --timeout 600 --retries 5 pip setuptools wheel && \
    python -m pip config set global.timeout 600 && \
    python -m pip config set global.retries 5
# 如需国内镜像（可选）：
# RUN python -m pip config set global.index-url https://mirrors.aliyun.com/pypi/simple

# ===== 安装 cython + qlib + 依赖 =====
RUN python -m pip install -U --timeout 600 --retries 5 Cython==0.29.37
RUN python -m pip install -e .
RUN python -m pip install --no-cache-dir --timeout 600 --retries 5 \
      catboost xgboost scipy==1.11.4 tables
FROM pytorch/pytorch:2.2.1-cuda12.1-cudnn8-runtime

# --- Build-time proxy (with defaults) ---
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

# 代理与 APT 源（保持不变）
ARG HTTP_PROXY=http://172.17.0.1:7890
ARG HTTPS_PROXY=http://172.17.0.1:7890
ARG NO_PROXY=localhost,127.0.0.1,.local,registry-1.docker.io

ENV http_proxy=${HTTP_PROXY}
ENV https_proxy=${HTTPS_PROXY}
ENV no_proxy=${NO_PROXY}

RUN printf 'Acquire::http::Proxy "%s";\nAcquire::https::Proxy "%s";\n' "$http_proxy" "$https_proxy" \
    > /etc/apt/apt.conf.d/90proxy

RUN sed -i 's|http://archive.ubuntu.com/ubuntu/|http://mirrors.aliyun.com/ubuntu/|g; \
            s|http://security.ubuntu.com/ubuntu|http://mirrors.aliyun.com/ubuntu|g' \
    /etc/apt/sources.list

# 先安装 git，再配置 git 代理（顺序非常重要）
RUN apt-get clean && apt-get update && apt-get install -y \
      curl vim git build-essential coreutils ca-certificates \
  && git --version \
  && git config --global http.proxy  "$http_proxy"  || true \
  && git config --global https.proxy "$https_proxy" || true \
  && rm -rf /var/lib/apt/lists/* \

# For GPU support, please choose the proper tag from https://hub.docker.com/r/pytorch/pytorch/tags

RUN apt-get clean && apt-get update && apt-get install -y \  
    curl \  
    vim \  
    git \  
    build-essential \
    coreutils \
    && rm -rf /var/lib/apt/lists/* 

RUN git clone https://github.com/microsoft/qlib.git

WORKDIR /workspace/qlib

RUN git fetch && git reset 3e72593b8c985f01979bebcf646658002ac43b00 --hard

RUN python -m pip install --upgrade cython
RUN python -m pip install -e .

RUN pip install catboost
RUN pip install xgboost
RUN pip install scipy==1.11.4
RUN pip install tables

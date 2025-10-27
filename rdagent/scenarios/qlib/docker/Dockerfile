FROM pytorch/pytorch:2.2.1-cuda12.1-cudnn8-runtime

# --- Build-time proxy (with defaults) ---
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

# 下行默认值就是你想要的 127.0.0.1:7890；如果外部没传 --build-arg，就用这里的默认
ENV http_proxy=${HTTP_PROXY:-http://127.0.0.1:7890}
ENV https_proxy=${HTTPS_PROXY:-http://127.0.0.1:7890}
ENV no_proxy=${NO_PROXY:-localhost,127.0.0.1,.local,registry-1.docker.io}

# 让 git 也用代理（clone 不再卡）
RUN git config --global http.proxy  "${http_proxy}"  && \
    git config --global https.proxy "${https_proxy}"
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

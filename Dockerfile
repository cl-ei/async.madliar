FROM python:3.13.14

EXPOSE 10090

ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN echo 'export LANG="C.UTF-8"' >> /etc/profile

# ---- Node ----
# marked 18 要求 Node >= 20，而 bookworm 源里的 nodejs 是 18.19，版本不够，只能用官方二进制。
# NODE_MIRROR 用 npmmirror（国内源）；装不上就用构建参数换成 https://nodejs.org/dist
ARG NODE_VERSION=22.14.0
ARG NODE_MIRROR=https://npmmirror.com/mirrors/node
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        ca-certificates curl xz-utils \
        libavif-dev \
    ; \
    rm -rf /var/lib/apt/lists/*; \
    case "$(uname -m)" in \
        x86_64|amd64)  NODE_ARCH=x64 ;; \
        aarch64|arm64) NODE_ARCH=arm64 ;; \
        *) echo "unsupported arch: $(uname -m)" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "${NODE_MIRROR}/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${NODE_ARCH}.tar.xz" -o /tmp/node.tar.xz; \
    tar -xJf /tmp/node.tar.xz -C /opt; \
    mv "/opt/node-v${NODE_VERSION}-linux-${NODE_ARCH}" /opt/node; \
    ln -sf /opt/node/bin/node /usr/local/bin/node; \
    ln -sf /opt/node/bin/npm  /usr/local/bin/npm; \
    rm -f /tmp/node.tar.xz; \
    node --version

ENV RUN_ENV prod

WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . ./

CMD ["python", "run.py"]

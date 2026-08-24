FROM python:3.13.14

EXPOSE 10090

ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN echo 'export LANG="C.UTF-8"' >> /etc/profile

RUN apt-get update \
    && apt-get install -y --no-install-recommends libavif-dev \
    && rm -rf /var/lib/apt/lists/*

ENV RUN_ENV prod

WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . ./

CMD ["python", "run.py"]

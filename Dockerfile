FROM python:3.13.14

EXPOSE 10090

ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN echo 'export LANG="C.UTF-8"' >> /etc/profile


WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . ./

CMD ["python", "run.py"]

FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir langchain-community langchain-aws && \
    pip cache purge

COPY . .

# AWS CLIをインストール
RUN apt-get update && apt-get install -y awscli

# AWS認証情報をコピーするためのディレクトリを作成
RUN mkdir -p /root/.aws

COPY startup.sh .
RUN chmod +x startup.sh

EXPOSE 8501

CMD ["./startup.sh"]
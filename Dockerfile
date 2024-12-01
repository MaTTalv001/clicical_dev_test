FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir langchain-community langchain-aws awscli && \
    pip cache purge

# startup.shをコピーして実行権限を付与
COPY startup.sh .
RUN chmod +x /app/startup.sh

# AWS認証情報用のディレクトリを作成
RUN mkdir -p /root/.aws

EXPOSE 8501

CMD ["sh", "./startup.sh"]
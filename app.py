import streamlit as st
import boto3
import os
from langchain_community.chat_models import BedrockChat

# AWSの認証情報を環境変数から取得
os.environ['AWS_ACCESS_KEY_ID'] = st.secrets["AWS_ACCESS_KEY_ID"]
os.environ['AWS_SECRET_ACCESS_KEY'] = st.secrets["AWS_SECRET_ACCESS_KEY"]
os.environ['AWS_DEFAULT_REGION'] = st.secrets["AWS_DEFAULT_REGION"]

# Bedrockクライアントの設定
bedrock = boto3.client('bedrock-runtime')

# BedrockChatモデルの初期化
llm = BedrockChat(model_id="anthropic.claude-v2:1", client=bedrock)

st.title("Bedrock Chat Application")

# ユーザー入力
user_input = st.text_input("Enter your message:")

if st.button("Send"):
    if user_input:
        response = llm.invoke(user_input)
        st.write("Response:", response.content)
    else:
        st.write("Please enter a message.")
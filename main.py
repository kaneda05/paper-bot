import os
import time
import requests
import random
import xml.etree.ElementTree as ET
from google import genai

# GitHub SecretsからAPIキーを取得
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_USER_ID = os.getenv('LINE_USER_ID')

KEYWORDS = ["natural language processing", "Generation AI", "Advertising"]

def fetch_arxiv_paper(keyword):
    url = "http://export.arxiv.org/api/query"
    random_start_index = random.randint(0, 10)
    params = {
        "search_query": f'all:"{keyword}"',
        "start": random_start_index,
        "max_results": 1,
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    }
    max_retries = 3
    for attempt in range(max_retries):
        try:
            time.sleep(3)
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 429:
                time.sleep(15 * (attempt + 1))
                continue
            response.raise_for_status()
            root = ET.fromstring(response.text)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            entry = root.find('atom:entry', ns)
            if entry is None: return None
            title = entry.find('atom:title', ns).text.replace('\n', ' ').strip()
            abstract = entry.find('atom:summary', ns).text.replace('\n', ' ').strip()
            published = entry.find('atom:published', ns).text[:10]
            link = entry.find('atom:id', ns).text
            return {'title': title, 'abstract': abstract, 'year': published, 'id': link}
        except:
            if attempt < max_retries - 1: time.sleep(5)
            else: return None
    return None

def summarize_paper(paper_data, client):
    prompt = f"""
あなたは最新テクノロジーを分かりやすく解説する、優秀なITコンサルタントです。
以下の英語論文の要約（Abstract）を分析し、中高生でも理解できるレベルまで噛み砕いて日本語で要約してください。

【絶対遵守のルール】
1. AIとしての挨拶、前置き、後書き、自己紹介、感想は「一切」出力しないでください。
2. 口調は、感情を交えないプロフェッショナルな「です・ます」調で統一してください。
3. 専門用語が登場する場合は、必ず「適切な日本語訳（English Term）」の形式で併記してください。
4. 以下の【出力フォーマット】の項目名と構造に完全に絶対に従い、それ以外のテキストは出力しないでください。

【論文タイトル】: {paper_data['title']}
【内容】: {paper_data['abstract']}

【出力フォーマット】
■ 背景・目的
（概要を記載）

■ アプローチ
（手法を記載）

■ 結論・知見
（成果を記載）
"""
    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text
    except Exception as e:
        return f"⚠️ 要約エラー: {e}"

def send_to_line(message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    payload = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": message}]}
    requests.post(url, headers=headers, json=payload)

def main():
    if not all([GEMINI_API_KEY, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID]):
        print("❌ 必要な環境変数が設定されていません。")
        return
    client = genai.Client(api_key=GEMINI_API_KEY)
    for kw in KEYWORDS:
        paper = fetch_arxiv_paper(kw)
        if paper:
            summary = summarize_paper(paper, client)
            msg = (f"━━━━━━━━━━━━━━\n🌟 【{kw}】最新論文レポート\n━━━━━━━━━━━━━━\n"
                   f"📖 TITLE: {paper['title']}\n📅 PUBLISHED: {paper['year']}\n━━━━━━━━━━━━━━\n\n"
                   f"{summary}\n\n🔗 論文詳細: {paper['id']}\n━━━━━━━━━━━━━━")
            send_to_line(msg)
            time.sleep(10)

if __name__ == "__main__":
    main()
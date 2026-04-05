import os
import time
import requests
import random
import xml.etree.ElementTree as ET
from google import genai

# ==========================================
# 設定エリア：ここを書き換えるだけでOK
# ==========================================
# 検索したいキーワードをリストで指定（複数指定すると「いずれかを含む」になります）
KEYWORDS = ["Advertising", "Marketing Automation", "Ad Tech"]
# 取得する論文の数
NUM_PAPERS = 5
# ==========================================

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_USER_ID = os.getenv('LINE_USER_ID')

def build_arxiv_query(keywords):
    """キーワードリストからarXiv用の検索クエリ文字列を作成する"""
    # 例: (all:"Advertising" OR all:"Marketing Automation") という形式にする
    query_parts = [f'all:"{k}"' for k in keywords]
    return "(" + " OR ".join(query_parts) + ")"

def fetch_arxiv_papers(query, num_papers=5):
    """arXiv APIから本物の論文データを取得する"""
    url = "http://export.arxiv.org/api/query"
    # 毎回同じ結果にならないよう、少しランダムに開始位置をずらす
    random_start = random.randint(0, 20)
    
    params = {
        "search_query": query,
        "start": random_start,
        "max_results": num_papers,
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        papers = []
        for entry in root.findall('atom:entry', ns):
            papers.append({
                'title': entry.find('atom:title', ns).text.replace('\n', ' ').strip(),
                'abstract': entry.find('atom:summary', ns).text.replace('\n', ' ').strip(),
                'year': entry.find('atom:published', ns).text[:10],
                'id': entry.find('atom:id', ns).text
            })
        return papers
    except Exception as e:
        print(f"Fetch error: {e}")
        return []

def summarize_paper(paper_data, client):
    """Geminiによる高品質な要約生成"""
    prompt = f"""
あなたは日本の大手広告代理店のシニアコンサルタントです。
以下の論文を読み、日本の広告実務に即した要約とアドバイスを作成してください。

・タイトル: {paper_data['title']}
・内容: {paper_data['abstract']}

【出力形式】
■ 背景・課題
■ 解決アプローチ
■ 結論・成果
💡 実務への落とし込みアイデア（日本の現場視点で2〜3行）

※専門用語（ROAS, CVR等）を適切に使い、ビジネス日本語で記述すること。前置きは不要。
"""
    try:
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return response.text
    except:
        return "要約生成に失敗しました。"

def send_to_line(message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    payload = {"to": LINE_USER_ID, "messages": [{"type": "text", "text": message}]}
    requests.post(url, headers=headers, json=payload)

def main():
    if not all([GEMINI_API_KEY, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID]):
        return
        
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # 検索クエリの組み立て
    query = build_arxiv_query(KEYWORDS)
    print(f"Searching for: {query}")
    
    papers = fetch_arxiv_papers(query, NUM_PAPERS)
    
    if not papers:
        send_to_line("⚠️ 論文が見つかりませんでした。")
        return
        
    for i, paper in enumerate(papers):
        summary = summarize_paper(paper, client)
        msg = (f"━━━━━━━━━━━━━━\n🌟 広告論文速報 ({i+1}/{NUM_PAPERS})\n━━━━━━━━━━━━━━\n"
               f"📖 {paper['title']}\n📅 {paper['year']}\n━━━━━━━━━━━━━━\n\n"
               f"{summary}\n\n🔗 原文: {paper['id']}\n━━━━━━━━━━━━━━")
        send_to_line(msg)
        time.sleep(5)

if __name__ == "__main__":
    main()
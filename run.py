import re
import random
import json
import requests
from flask import Flask, request, jsonify, render_template, send_from_directory

app = Flask(__name__, static_folder='static', template_folder='static')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://blog.csdn.net/"
}

API = "https://blog.csdn.net/phoenix/web/v1/comment/list/{article_id}"


def extract_article_id(url: str) -> str:
    """从任意 CSDN 文章 URL 里抠出 articleId"""
    m = re.search(r"article/details/(\d+)", url)
    if not m:
        raise ValueError("无法解析文章 ID，请检查链接")
    return m.group(1)


def fetch_all_comments(article_id: str, include_fold: bool = False, include_replies: bool = False):
    """分页拉取全部评论"""
    # 定义需要获取的评论类型
    fold_types = ["unfold"]  # 默认只获取不折叠的评论
    if include_fold:
        fold_types.append("fold")  # 如果需要，也获取折叠的评论
    
    comments = []
    for fold in fold_types:
        page = 1
        while True:
            params = {"page": page, "pageSize": 100, "fold": fold}
            resp = requests.get(API.format(article_id=article_id),
                                headers=HEADERS, params=params, timeout=15)
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")

            data = resp.json()
            if data["code"] != 200:
                raise RuntimeError(f'接口错误: {data["message"]}')

            items = data["data"]["list"]
            if not items:
                break  # 拉完了

            for item in items:
                # 处理主评论
                info = item["info"]
                # 尝试从不同字段获取用户标识
                username = info.get("username", "")
                if not username:
                    username = info.get("userId", "")
                if not username:
                    username = info.get("userName", "")
                if not username:
                    username = info.get("id", "")
                comments.append({
                    "nickName": info["nickName"],
                    "content": info["content"],
                    "username": username  # 获取用户名，用于构建主页链接
                })
                
                # 处理回复评论
                if include_replies and "sub" in item and item["sub"]:
                    for reply in item["sub"]:
                        # 尝试从不同字段获取用户标识
                        reply_username = reply.get("username", "")
                        if not reply_username:
                            reply_username = reply.get("userId", "")
                        if not reply_username:
                            reply_username = reply.get("userName", "")
                        if not reply_username:
                            reply_username = reply.get("id", "")
                        comments.append({
                            "nickName": reply["nickName"],
                            "content": reply["content"],
                            "username": reply_username  # 获取用户名，用于构建主页链接
                        })

            page += 1
    return comments


def deduplicate_comments(comments):
    """去重评论，同一个用户只保留一条"""
    seen_users = set()
    unique_comments = []
    for comment in comments:
        # 使用nickName作为去重标识
        if comment["nickName"] not in seen_users:
            seen_users.add(comment["nickName"])
            unique_comments.append(comment)
    return unique_comments


def run_lottery(comments, winner_count=1):
    """运行抽奖，返回指定数量的获奖者"""
    if not comments:
        return []
    # 随机选择获奖者
    winners = random.sample(comments, min(winner_count, len(comments)))
    return winners


@app.route('/')
def index():
    """首页"""
    return render_template('index.html')


@app.route('/api/fetch_comments', methods=['POST'])
def api_fetch_comments():
    """获取评论API"""
    try:
        data = request.json
        url = data.get('url', '')
        include_fold = data.get('include_fold', False)
        include_replies = data.get('include_replies', False)
        
        if not url:
            return jsonify({"success": False, "message": "请输入文章链接"})
        
        article_id = extract_article_id(url)
        comments = fetch_all_comments(article_id, include_fold, include_replies)
        unique_comments = deduplicate_comments(comments)
        
        return jsonify({
            "success": True,
            "total_comments": len(comments),
            "unique_comments": len(unique_comments),
            "comments": comments  # 返回所有评论，不进行去重
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route('/api/run_lottery', methods=['POST'])
def api_run_lottery():
    """运行抽奖API"""
    try:
        data = request.json
        url = data.get('url', '')
        include_fold = data.get('include_fold', False)
        include_replies = data.get('include_replies', False)
        winner_count = data.get('winner_count', 1)
        
        if not url:
            return jsonify({"success": False, "message": "请输入文章链接"})
        
        article_id = extract_article_id(url)
        comments = fetch_all_comments(article_id, include_fold, include_replies)
        unique_comments = deduplicate_comments(comments)
        
        if not unique_comments:
            return jsonify({"success": False, "message": "没有评论可用于抽奖"})
        
        winners = run_lottery(unique_comments, winner_count)
        
        return jsonify({
            "success": True,
            "total_comments": len(comments),
            "unique_comments": len(unique_comments),
            "winners": winners
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8100)
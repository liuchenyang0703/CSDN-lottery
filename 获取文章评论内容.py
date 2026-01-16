import re
import sys
import json
import requests

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
                yield info["nickName"], info["content"], False  # False表示主评论
                
                # 处理回复评论
                if include_replies and "sub" in item and item["sub"]:
                    for reply in item["sub"]:
                        yield reply["nickName"], reply["content"], True  # True表示回复评论

            page += 1


def main():
    url = input("请输入 CSDN 文章链接：").strip()
    try:
        article_id = extract_article_id(url)
    except ValueError as e:
        print(e)
        sys.exit(1)

    fold_choice = input("是否查询折叠评论？(y/n 默认 n)：").strip().lower()
    include_fold = fold_choice == "y"
    
    replies_choice = input("是否包含回复评论？(y/n 默认 n)：").strip().lower()
    include_replies = replies_choice == "y"

    print("\n开始拉取评论，请稍候...\n")
    try:
        for idx, (nick, content, is_reply) in enumerate(fetch_all_comments(article_id, include_fold, include_replies), 1):
            # 简单去掉 CSDN 表情标签，让内容更干净
            content = re.sub(r"\[face[^\]]*\]", "", content)
            if is_reply:
                print(f"{idx:04d} | 回复 | {nick}")
                print(f"      > {content}\n")
            else:
                print(f"{idx:04d} | 主评论 | {nick}")
                print(f"      {content}\n")
    except Exception as e:
        print("发生异常：", e)
        sys.exit(1)

    print("=== 全部评论已列出 ===")


if __name__ == "__main__":
    main()
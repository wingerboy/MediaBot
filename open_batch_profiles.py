#!/usr/bin/env python3
"""
批量打开推特用户主页，每次10个，按Enter切换下一组。
"""
import os
import time

BATCH_SIZE = 10
X_FILE = "x.txt"

def parse_user_list(file_path):
    users = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("http"):
                users.append(line)
            else:
                users.append(f"https://twitter.com/{line}")
    return users

def open_batch(urls):
    for url in urls:
        os.system(f'open "{url}"')
        time.sleep(0.2)  # 避免浏览器卡顿

if __name__ == "__main__":
    users = parse_user_list(X_FILE)
    total = len(users)
    batch_num = 0
    for i in range(0, total, BATCH_SIZE):
        batch = users[i:i+BATCH_SIZE]
        batch_num += 1
        print(f"\n=== 第{batch_num}组，共{len(batch)}个账号 ===")
        open_batch(batch)
        input("请手动关注，完成后按Enter继续下一组...")

    print("全部账号已处理完毕！") 
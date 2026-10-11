#!/usr/bin/env python3
"""
QuickBox 文件上传脚本
用法: python upload_file.py <文件路径> [选项]
"""

import os
import sys
import requests
import argparse
import json

DEFAULT_API_URL = "http://localhost:8089"
DEFAULT_HOST = os.getenv("QUICKBOX_HOST", "")
CHUNK_SIZE = 5242880  # 5MB


def upload_file(file_path, api_url=DEFAULT_API_URL, host=DEFAULT_HOST):
    """上传文件到 QuickBox"""
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在: {file_path}")
        return None
    
    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    
    print(f"📁 文件: {filename} ({file_size} bytes)")
    
    # 1. 初始化上传
    print("🔄 初始化上传...")
    init_url = f"{api_url}/api/upload/init"
    init_data = {
        "filename": filename,
        "totalSize": file_size,
        "chunkSize": CHUNK_SIZE,
        "totalChunks": 1
    }
    
    try:
        resp = requests.post(init_url, json=init_data, timeout=30)
        result = resp.json()
        
        if result.get("code") != 200:
            print(f"❌ 初始化失败: {result.get('message')}")
            return None
        
        upload_id = result["data"]["uploadId"]
        chunk_path = result["data"]["chunkPath"]
        print(f"✅ 上传ID: {upload_id}")
        
        # 2. 上传文件内容
        print("📤 上传文件...")
        with open(file_path, "rb") as f:
            upload_url = f"{api_url}/api/upload/upload"
            files = {
                "file": (filename, f, "application/octet-stream"),
                "uploadId": (None, upload_id),
                "chunkNumber": (None, "1"),
                "totalChunks": (None, "1"),
                "totalSize": (None, str(file_size)),
                "filename": (None, filename)
            }
            upload_resp = requests.post(upload_url, files=files, timeout=60)
            upload_result = upload_resp.json()
            
            if upload_result.get("code") != 200:
                print(f"❌ 上传失败: {upload_result.get('message')}")
                return None
        
        print("✅ 文件上传成功!")
        
        # 3. 合并分片获取取件码
        print("🔗 合并文件...")
        merge_url = f"{api_url}/api/upload/merge?accessCode={upload_id}"
        merge_resp = requests.post(merge_url, timeout=30)
        merge_result = merge_resp.json()
        
        if merge_result.get("code") != 200:
            print(f"❌ 合并失败: {merge_result.get('message')}")
            return None
        
        access_code = merge_result.get("data")
        print(f"✅ 取件码: {access_code}")
        
        # 使用主机 IP 构建下载链接 (正确 API 路径: /api/upload/download/)
        download_link = f"http://{host}:8083/api/upload/download/{access_code}"
        
        return {
            "accessCode": access_code,
            "downloadUrl": download_link,
            "infoUrl": f"http://{host}:8083/api/upload/info/{access_code}",
            "filename": filename,
            "fileSize": file_size
        }
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="上传文件到 QuickBox")
    parser.add_argument("file", help="要上传的文件路径")
    parser.add_argument("--api", default=DEFAULT_API_URL, help="API 地址")
    parser.add_argument("--host", default=DEFAULT_HOST, help="主机 IP")
    parser.add_argument("--output", choices=["code", "link", "json"], default="json", help="输出格式")
    
    args = parser.parse_args()
    
    result = upload_file(args.file, args.api, args.host)
    
    if result:
        if args.output == "code":
            print(result["accessCode"])
        elif args.output == "link":
            print(result["downloadUrl"])
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 同时输出临时链接供复制
        print(f"\n📎 临时下载链接: {result['downloadUrl']}")
        print(f"🔑 取件码: {result['accessCode']}")
        print(f"⏰ 有效期: 7 天或下载后立即失效")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
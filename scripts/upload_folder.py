#!/usr/bin/env python3
"""
QuickBox 文件夹上传脚本
用法: python upload_folder.py <文件夹路径> [选项]
"""

import os
import sys
import requests
import argparse
import json
import zipfile
import io

DEFAULT_API_URL = "http://localhost:8089"
DEFAULT_HOST = os.getenv("QUICKBOX_HOST", "")


def get_folder_size(folder_path):
    """计算文件夹大小"""
    total = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total += os.path.getsize(fp)
    return total


def upload_folder(folder_path, api_url=DEFAULT_API_URL, host=DEFAULT_HOST):
    """上传文件夹到 QuickBox"""
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        print(f"错误: 文件夹不存在: {folder_path}")
        return None
    
    folder_name = os.path.basename(folder_path)
    total_size = get_folder_size(folder_path)
    
    print(f"📁 文件夹: {folder_name} ({total_size} bytes)")
    
    # 1. 创建 ZIP 文件
    print("📦 打包文件夹...")
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                zf.write(file_path, arcname)
    
    zip_size = zip_buffer.tell()
    zip_buffer.seek(0)
    
    print(f"✅ ZIP 大小: {zip_size} bytes")
    
    # 2. 初始化文件夹上传
    print("🔄 初始化文件夹上传...")
    init_url = f"{api_url}/api/upload/folder/init"
    init_data = {
        "folderName": folder_name,
        "totalFiles": sum([len(files) for r, d, files in os.walk(folder_path)]),
        "totalSize": zip_size,
        "autoZip": True,
        "keepStructure": True
    }
    
    try:
        resp = requests.post(init_url, json=init_data, timeout=30)
        result = resp.json()
        
        if result.get("code") != 200:
            print(f"❌ 初始化失败: {result.get('message')}")
            return None
        
        session_id = result["data"]["sessionId"]
        access_code = result["data"]["accessCode"]
        print(f"✅ 会话ID: {session_id}")
        print(f"✅ 取件码: {access_code}")
        
        # 3. 上传 ZIP 文件 (作为单文件分片上传)
        print("📤 上传 ZIP 文件...")
        upload_url = f"{api_url}/api/upload/folder/chunk"
        
        files = {
            "file": (f"{folder_name}.zip", zip_buffer, "application/zip"),
            "sessionId": (None, session_id),
            "chunkNumber": (None, "1"),
            "totalChunks": (None, "1"),
            "totalSize": (None, str(zip_size)),
            "identifier": (None, folder_name),
            "filename": (None, f"{folder_name}.zip"),
            "isZipUpload": (None, "true")
        }
        
        upload_resp = requests.post(upload_url, files=files, timeout=300)
        upload_result = upload_resp.json()
        
        if upload_result.get("code") != 200:
            print(f"❌ 上传失败: {upload_result.get('message')}")
            return None
        
        print("✅ 文件上传成功!")
        
        # 4. 合并文件夹
        print("🔗 合并文件夹...")
        merge_url = f"{api_url}/api/upload/folder/merge"
        merge_data = {"sessionId": session_id}
        merge_resp = requests.post(merge_url, json=merge_data, timeout=60)
        merge_result = merge_resp.json()
        
        if merge_result.get("code") != 200:
            print(f"❌ 合并失败: {merge_result.get('message')}")
            return None
        
        print("✅ 文件夹处理完成!")
        
        # 使用主机 IP 构建下载链接 (正确 API 路径: /api/upload/folder/download/)
        download_link = f"http://{host}:8083/api/upload/folder/download/{access_code}"
        
        return {
            "accessCode": access_code,
            "downloadUrl": download_link,
            "infoUrl": f"http://{host}:8083/api/upload/folder/info/{access_code}",
            "folderName": folder_name,
            "folderSize": total_size,
            "zipSize": zip_size
        }
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="上传文件夹到 QuickBox")
    parser.add_argument("folder", help="要上传的文件夹路径")
    parser.add_argument("--api", default=DEFAULT_API_URL, help="API 地址")
    parser.add_argument("--host", default=DEFAULT_HOST, help="主机 IP")
    parser.add_argument("--output", choices=["code", "link", "json"], default="json", help="输出格式")
    
    args = parser.parse_args()
    
    result = upload_folder(args.folder, args.api, args.host)
    
    if result:
        if args.output == "code":
            print(result["accessCode"])
        elif args.output == "link":
            print(result["downloadUrl"])
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        print(f"\n📎 临时下载链接: {result['downloadUrl']}")
        print(f"🔑 取件码: {result['accessCode']}")
        print(f"⏰ 有效期: 7 天或下载后立即失效")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
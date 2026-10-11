---
name: quickbox-upload
description: "上传文件到 QuickBox (快取柜) 并获取临时分享链接。使用场景：(1) 需要临时分享文件给他人，(2) 文件中转传输，(3) 生成可下载的临时链接。当用户提到上传文件到快取柜、生成临时文件链接、分享文件、临时文件存储时使用此技能。"
---

# QuickBox 文件上传技能

此技能用于将文件上传到 QuickBox (快取柜) 并获取临时分享链接。

## 快速开始

### 1. 上传文件

```bash
# 上传文件（主机由 --host 或 QUICKBOX_HOST 指定）
python3 scripts/upload_file.py /path/to/file.pdf

# 指定主机 IP
python3 scripts/upload_file.py /path/to/file.pdf --host 192.168.1.100

# 输出取件码
python3 scripts/upload_file.py /path/to/file.pdf --output code
```

### 2. 上传文件夹

```bash
python3 scripts/upload_folder.py /path/to/folder
```

```python
import requests

def upload_file(file_path, api_url="http://localhost:8089"):
    """上传文件到 QuickBox"""
    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    
    # 1. 初始化上传
    init_url = f"{api_url}/api/upload/init"
    init_data = {
        "filename": filename,
        "totalSize": file_size,
        "chunkSize": 5242880,
        "totalChunks": 1
    }
    resp = requests.post(init_url, json=init_data)
    result = resp.json()
    upload_id = result["data"]["uploadId"]
    
    # 2. 上传文件内容
    with open(file_path, "rb") as f:
        upload_url = f"{api_url}/api/upload/upload"
        files = {
            "file": (filename, f, "application/octet-stream"),
            "uploadId": upload_id,
            "chunkNumber": 1,
            "totalChunks": 1
        }
        requests.post(upload_url, files=files)
    
    # 3. 获取取件码
    merge_url = f"{api_url}/api/upload/merge"
    merge_resp = requests.post(merge_url, json={"accessCode": upload_id})
    return upload_id

def get_download_link(access_code, api_url="http://localhost:8089"):
    """获取下载链接"""
    info_url = f"{api_url}/api/upload/info/{access_code}"
    resp = requests.get(info_url)
    data = resp.json()["data"]
    return f"{api_url}{data['downloadUrl']}"
```

## 脚本使用

### 上传文件 (scripts/upload_file.py)

```bash
# 上传文件
python scripts/upload_file.py /path/to/file.pdf

# 指定 API 地址
python scripts/upload_file.py /path/to/file.pdf --api http://192.168.1.100:8089

# 输出取件码
python scripts/upload_file.py /path/to/file.pdf --output code

# 输出完整下载链接
python scripts/upload_file.py /path/to/file.pdf --output link
```

### 上传文件夹 (scripts/upload_folder.py)

```bash
# 上传整个文件夹
python scripts/upload_folder.py /path/to/folder

# 指定 API 地址
python scripts/upload_folder.py /path/to/folder --api http://192.168.1.100:8089
```

## API 接口说明

### 文件上传

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/upload/init` | POST | 初始化上传，获取 uploadId |
| `/api/upload/upload` | POST | 上传分片文件 |
| `/api/upload/merge` | POST | 合并分片，获取取件码 |
| `/api/upload/info/{accessCode}` | GET | 获取文件信息 |
| `/api/upload/download/{accessCode}` | GET | 下载文件 |

### 文件夹上传

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/upload/folder/init` | POST | 初始化文件夹上传 |
| `/api/upload/folder/chunk` | POST | 上传文件夹分片 |
| `/api/upload/folder/merge` | POST | 合并文件夹 |
| `/api/upload/folder/download/{accessCode}` | GET | 下载文件夹 |

## 配置

默认配置 (可在脚本中修改):
- API 地址: `http://localhost:8089`
- 取件码长度: 6 位
- 文件有效期: 7 天
- 分片大小: 5MB

## 注意事项

1. 文件下载后立即自动删除
2. 取件码 7 天后自动过期
3. 每个取件码只能使用一次
4. 最大文件大小: 100MB
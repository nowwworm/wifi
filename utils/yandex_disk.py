import os
import httpx
from config import YANDEX_DISK_TOKEN

async def create_folder(folder_path: str) -> bool:
    """
    Creates a folder on Yandex.Disk if it doesn't exist.
    """
    url = "https://cloud-api.yandex.net/v1/disk/resources"
    headers = {
        "Authorization": f"OAuth {YANDEX_DISK_TOKEN}"
    }
    params = {
        "path": folder_path
    }
    
    async with httpx.AsyncClient() as client:
        # Try to create the folder
        response = await client.put(url, headers=headers, params=params)
        if response.status_code == 201:
            return True
        elif response.status_code == 409:
            # 409 Conflict means the folder already exists
            return True
        return False

async def upload_file_to_yandex_disk(local_file_path: str, remote_file_name: str, folder_path: str = "feo2sport_edits") -> str:
    """
    Uploads a local file to Yandex.Disk and returns its path on the disk or error message.
    """
    # 1. Ensure the folder exists
    await create_folder(folder_path)
    
    # 2. Get the upload URL from Yandex Disk
    url = "https://cloud-api.yandex.net/v1/disk/resources/upload"
    headers = {
        "Authorization": f"OAuth {YANDEX_DISK_TOKEN}"
    }
    
    remote_path = f"{folder_path}/{remote_file_name}"
    params = {
        "path": remote_path,
        "overwrite": "true"
    }
    
    async with httpx.AsyncClient() as client:
        # Request upload URL
        response = await client.get(url, headers=headers, params=params)
        if response.status_code != 200:
            error_data = response.json()
            raise Exception(f"Failed to get upload URL: {error_data.get('message', response.text)}")
            
        upload_data = response.json()
        upload_url = upload_data.get("href")
        
        # 3. Upload the file to Yandex Disk
        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f"Local file not found: {local_file_path}")
            
        with open(local_file_path, "rb") as f:
            file_data = f.read()
            
        upload_response = await client.put(upload_url, content=file_data)
            
        if upload_response.status_code not in (201, 202):
            raise Exception(f"Upload failed: {upload_response.text}")
            
        return remote_path

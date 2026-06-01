import base64
import os
import logging
import httpx
from datetime import datetime
from config import GITHUB_TOKEN, GITHUB_REPO, GITHUB_FOLDER

logger = logging.getLogger(__name__)

async def upload_file_to_github(repo_path: str, content: bytes, commit_message: str) -> str:
    """
    Uploads a file to GitHub repository contents using the API.
    Returns the URL of the uploaded file on success, or raises an Exception.
    """
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN is not set in environment variables.")

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{repo_path}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "FeoSportBot"
    }

    # Encode content to base64 string
    content_b64 = base64.b64encode(content).decode("utf-8")

    data = {
        "message": commit_message,
        "content": content_b64
    }

    async with httpx.AsyncClient() as client:
        # Check if file exists to get SHA in case we need to update/overwrite it
        sha = None
        try:
            get_resp = await client.get(url, headers=headers)
            if get_resp.status_code == 200:
                sha = get_resp.json().get("sha")
                data["sha"] = sha
        except Exception as e:
            logger.warning(f"Error checking file existence for {repo_path}: {e}")

        # Put the file
        resp = await client.put(url, headers=headers, json=data)
        if resp.status_code not in (200, 201):
            logger.error(f"GitHub upload failed for {repo_path}: {resp.status_code} - {resp.text}")
            raise Exception(f"GitHub API returned {resp.status_code}: {resp.text}")

        resp_data = resp.json()
        html_url = resp_data.get("content", {}).get("html_url", "")
        return html_url

async def export_edit_to_github(edit) -> str:
    """
    Exports a single edit (markdown report and optional screenshot image) to GitHub.
    Returns the HTML URL of the created markdown file.
    """
    # 1. Handle image if present
    image_md = ""
    if edit.image_path and os.path.exists(edit.image_path):
        try:
            with open(edit.image_path, "rb") as img_file:
                img_data = img_file.read()
            
            # Format image path inside the repo: {folder}/images/edit_{id}.jpg
            # Using forward slashes for repo paths
            repo_folder = GITHUB_FOLDER.strip("/")
            repo_img_path = f"{repo_folder}/images/edit_{edit.id}.jpg" if repo_folder else f"images/edit_{edit.id}.jpg"
            
            await upload_file_to_github(
                repo_path=repo_img_path,
                content=img_data,
                commit_message=f"Upload screenshot for edit #{edit.id}"
            )
            
            # Since markdown is in {folder}/edit_{id}.md and image is in {folder}/images/edit_{id}.jpg,
            # the relative path is 'images/edit_{id}.jpg'
            image_md = f"\n## Скриншот\n![Скриншот](images/edit_{edit.id}.jpg)\n"
        except Exception as img_err:
            logger.error(f"Failed to upload image to GitHub for edit #{edit.id}: {img_err}", exc_info=True)
            image_md = f"\n## Скриншот\n*Ошибка загрузки скриншота на GitHub: {str(img_err)}*\n"

    # 2. Build Markdown content
    username = f"@{edit.client_username}" if edit.client_username else f"ID {edit.client_id}"
    date_str = edit.created_at.strftime("%d.%m.%Y %H:%M:%S") if edit.created_at else datetime.utcnow().strftime("%d.%m.%Y %H:%M:%S")
    
    text_content = edit.text_content or "[Без текстового описания]"
    
    md_content = (
        f"# Правка #{edit.id}\n\n"
        f"**От:** {username} (ID: {edit.client_id})\n"
        f"**Дата:** {date_str}\n\n"
        f"## Описание\n"
        f"{text_content}\n"
        f"{image_md}"
    )

    # 3. Upload Markdown file to GitHub
    repo_folder = GITHUB_FOLDER.strip("/")
    repo_md_path = f"{repo_folder}/edit_{edit.id}.md" if repo_folder else f"edit_{edit.id}.md"
    
    md_url = await upload_file_to_github(
        repo_path=repo_md_path,
        content=md_content.encode("utf-8"),
        commit_message=f"Add edit #{edit.id} from {username}"
    )
    
    return md_url

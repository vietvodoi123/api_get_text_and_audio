import asyncio
import aiohttp
from utils import fetch_chapter_content, split_text, call_audio_api

async def send_webhook(webhook_url, data):
    """Gửi request đến webhook một cách bất đồng bộ."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(webhook_url, json=data) as response:
                response_text = await response.text()
                if response.status == 200:
                    print(f"🔔 Webhook gửi thành công: {response_text}")
                else:
                    print(f"⚠️ Lỗi webhook (HTTP {response.status}): {response_text}")
        except Exception as e:
            print(f"❌ Lỗi khi gửi webhook: {e}")

async def process_task(task_id, req, start, end, tasks_store):
    tasks_store[task_id]['status'] = 'processing'

    async with aiohttp.ClientSession() as session:
        # Tạo danh sách các task theo thứ tự chương từ start đến end
        fetch_tasks = [
            fetch_chapter_content(
                session,
                req.base_url.replace("{x}", str(chap_num)),
                req.css_selector_title,
                req.css_selector_content, chap_num
            )
            for chap_num in range(start, end + 1)
        ]
        # asyncio.gather sẽ trả về danh sách các kết quả theo thứ tự của fetch_tasks
        chapters = await asyncio.gather(*fetch_tasks)

    # Hợp nhất nội dung các chương theo thứ tự
    group_content = "\n\n".join([title + "\n" + content for title, content in chapters])

    # Chèn <break time="0.3s"/> sau mỗi ký tự xuống dòng và cắt theo limit 3000 ký tự
    segments = split_text(group_content, 3000)

    # Gọi API tạo audio cho từng đoạn (song song)
    audio_tasks = [call_audio_api(segment) for segment in segments]
    audio_urls = await asyncio.gather(*audio_tasks)

    tasks_store[task_id]['status'] = 'completed'
    tasks_store[task_id]['audio_urls'] = audio_urls

    # Kiểm tra xem có webhook không
    if req.webhook_url:
        data = {
            "task_id": task_id,
            "story_id": req.story_id,
            "audio_urls": audio_urls,
            "chapters": {"from": start, "to": end},
        }
        # Gửi webhook bất đồng bộ
        await send_webhook(req.webhook_url, data)

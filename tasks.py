import asyncio
import aiohttp
from utils import fetch_chapter_content, split_text, call_audio_api

async def retry_call_audio_api(segment, max_retries=3, delay=2):
    """Gọi API tạo audio, nếu thất bại sẽ thử lại (tối đa max_retries lần)."""
    for attempt in range(1, max_retries + 1):
        print(f"🔄 Đang gọi API tạo audio (lần {attempt})...")
        audio_url = await call_audio_api(segment)
        if audio_url:
            print(f"✅ Audio tạo thành công: {audio_url}")
            return audio_url
        print(f"⚠️ Lỗi, thử lại sau {delay} giây...")
        await asyncio.sleep(delay)
    print("❌ Không thể tạo audio sau nhiều lần thử.")
    return None  # Nếu thử hết số lần mà vẫn thất bại thì trả về None

async def process_task(task_id, req, start, end, tasks_store):
    tasks_store[task_id] = {
        'status': 'processing',
        'log': [],
        'audio_urls': []
    }
    tasks_store[task_id]['log'].append("🚀 Bắt đầu xử lý task...")

    async with aiohttp.ClientSession() as session:
        print("📥 Đang lấy nội dung chương truyện...")
        tasks_store[task_id]['log'].append("📥 Đang lấy nội dung chương truyện...")

        fetch_tasks = [
            fetch_chapter_content(
                session,
                req.base_url.replace("{x}", str(chap_num)),
                req.css_selector_title,
                req.css_selector_content, chap_num
            )
            for chap_num in range(start, end + 1)
        ]
        chapters = await asyncio.gather(*fetch_tasks)

    print("📖 Nội dung đã tải xong, đang xử lý...")
    tasks_store[task_id]['log'].append("📖 Nội dung đã tải xong, đang xử lý...")

    # Hợp nhất nội dung
    group_content = "\n\n".join(f"{title}\n{content}" for title, content in chapters)

    # Cắt thành các đoạn nhỏ (tối đa 3000 ký tự)
    segments = split_text(group_content, 3000)
    print(f"🔀 Nội dung chia thành {len(segments)} đoạn.")
    tasks_store[task_id]['log'].append(f"🔀 Nội dung chia thành {len(segments)} đoạn.")

    # Gọi API tạo audio
    print("🎙️ Đang tạo audio...")
    tasks_store[task_id]['log'].append("🎙️ Đang tạo audio...")

    audio_tasks = [retry_call_audio_api(segment) for segment in segments]
    audio_urls = await asyncio.gather(*audio_tasks)

    # Cập nhật trạng thái
    tasks_store[task_id]['status'] = 'completed'
    tasks_store[task_id]['audio_urls'] = [url for url in audio_urls if url]
    tasks_store[task_id]['log'].append("✅ Hoàn thành!")

    print("✅ Task đã hoàn tất!")

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
    return None

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

    # Gửi tất cả yêu cầu API đồng thời
    print("🎙️ Đang gửi tất cả yêu cầu tạo audio đồng thời...")
    tasks_store[task_id]['log'].append("🎙️ Đang gửi tất cả yêu cầu tạo audio đồng thời...")

    # Gửi đồng thời tất cả request
    tasks = [call_audio_api(segment) for segment in segments]
    audio_urls = await asyncio.gather(*tasks)

    # Lọc các đoạn thất bại
    failed_segments = [(idx, segments[idx]) for idx, url in enumerate(audio_urls) if url is None]

    # Nếu có lỗi, thử lại với những đoạn bị lỗi
    max_retries = 3
    retry_delay = 20
    for retry in range(1, max_retries + 1):
        if not failed_segments:
            break  # Không còn lỗi thì thoát

        print(f"🔁 Thử lại {len(failed_segments)} đoạn (Lần {retry}) sau {retry_delay} giây...")
        tasks_store[task_id]['log'].append(f"🔁 Thử lại {len(failed_segments)} đoạn (Lần {retry}) sau {retry_delay} giây...")
        await asyncio.sleep(retry_delay)

        # Gửi lại các request bị lỗi
        retry_tasks = [call_audio_api(segment) for _, segment in failed_segments]
        retry_results = await asyncio.gather(*retry_tasks)

        # Cập nhật danh sách lỗi
        for i, (idx, _) in enumerate(failed_segments):
            if retry_results[i]:  # Nếu thành công, cập nhật vào danh sách audio_urls
                audio_urls[idx] = retry_results[i]

        # Cập nhật danh sách lỗi mới
        failed_segments = [(idx, segments[idx]) for idx, url in enumerate(audio_urls) if url is None]

    # Cập nhật trạng thái
    tasks_store[task_id]['status'] = 'completed'
    tasks_store[task_id]['audio_urls'] = [url for url in audio_urls if url]
    tasks_store[task_id]['log'].append("✅ Hoàn thành!")

    print("✅ Task đã hoàn tất!")

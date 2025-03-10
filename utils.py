import aiohttp
from bs4 import BeautifulSoup
import json

def extract_audio_url(raw_item: str) -> str:
    """
    raw_item là một chuỗi dạng:
      0:["$@1",["84cax6OBoTQBQZ1A2WV_h",null]]
      1:{"message":"","data":{"audiourl":"https://freetts.com/results/Yj7lDuPG.mp3",...},"code":200}
    Ta cần lấy audiourl trong dòng thứ hai.
    """
    lines = raw_item.split("\n")
    # lines[0] = 0:["$@1",[...]]
    # lines[1] = 1:{"message":"","data":{"audiourl":"https://..."},"code":200}

    if len(lines) < 2:
        return ""  # Không đủ dòng

    second_line = lines[1].strip()
    # second_line = 1:{"message":"","data":{"audiourl":"..."},...}
    # Ta bỏ "1:" đi, rồi parse JSON
    if ":" in second_line:
        # Tách phần "1:" ra, giữ lại JSON
        _, json_str = second_line.split(":", 1)
        json_str = json_str.strip()
        try:
            data_obj = json.loads(json_str)
            if "data" in data_obj and "audiourl" in data_obj["data"]:
                return data_obj["data"]["audiourl"]
        except json.JSONDecodeError:
            pass
    return ""
async def fetch_chapter_content(session, url, css_selector_title, css_selector_content,chap_num):
    async with session.get(url) as response:
        html = await response.text()
        soup = BeautifulSoup(html, 'html.parser')
        title_elem = soup.select_one(css_selector_title)
        content_elem = soup.select_one(css_selector_content)
        title = title_elem.get_text(separator=" ",strip=True) if title_elem else "Tiêu đề không tìm thấy"
        content = content_elem.get_text(separator="\n", strip=True) if content_elem else "Nội dung không tìm thấy"

        return f"Chương {chap_num} "+title, content


def split_text(text, limit):
    """
    - Chèn <break time="0.3s"/> sau mỗi ký tự xuống dòng (\n).
    - Tách văn bản thành các dòng, sau đó nối các dòng lại thành các đoạn sao cho:
       + Độ dài mỗi đoạn < limit (ở đây limit = 3000).
       + Cố gắng tối ưu, tránh trường hợp có các đoạn quá nhỏ.
    - Nếu 1 dòng vượt quá limit, sẽ được chia thành các khúc nhỏ hơn.
    """
    # Bước 1: Chèn break tag sau mỗi ký tự xuống dòng
    text_with_break = text.replace("\n", "\n<break time=\"0.3s\"/>")

    # Bước 2: Tách thành danh sách các dòng
    lines = text_with_break.split("\n")

    segments = []
    current_segment = ""

    for line in lines:
        # Nếu 1 dòng dài hơn limit, cần chia nhỏ dòng đó trước
        if len(line) >= limit:
            # Nếu còn dữ liệu trong current_segment, lưu lại trước khi xử lý dòng dài
            if current_segment:
                segments.append(current_segment.strip())
                current_segment = ""
            # Chia dòng thành các khúc nhỏ (đảm bảo mỗi khúc < limit)
            start = 0
            while start < len(line):
                chunk = line[start:start + limit - 1]  # dùng limit-1 để đảm bảo nhỏ hơn limit
                segments.append(chunk)
                start += limit - 1
        else:
            # Nếu current_segment trống thì gán luôn dòng hiện tại
            if not current_segment:
                current_segment = line
            else:
                # Nếu nối dòng mới (có thêm 1 ký tự cho '\n') không vượt quá limit, nối lại
                if len(current_segment) + 1 + len(line) < limit:
                    current_segment = current_segment + "\n" + line
                else:
                    # Nếu không nối được, lưu current_segment và bắt đầu dòng mới
                    segments.append(current_segment.strip())
                    current_segment = line
    # Nếu còn dư current_segment
    if current_segment:
        segments.append(current_segment.strip())

    # THỬ: Sau đó thực hiện merge thêm 1 lượt để gom các đoạn nhỏ liền kề lại (nếu có)
    merged_segments = []
    buffer = ""
    for seg in segments:
        if not buffer:
            buffer = seg
        else:
            if len(buffer) + 1 + len(seg) < limit:
                buffer = buffer + "\n" + seg
            else:
                merged_segments.append(buffer)
                buffer = seg
    if buffer:
        merged_segments.append(buffer)

    # In ra độ dài các đoạn để kiểm tra
    # lengths = [len(s) for s in merged_segments]
    # print(lengths, len(lengths))
    # print(merged_segments)
    return merged_segments

async def call_audio_api(segment):
    url = "https://freetts.com/text-to-speech"

    headers = {
        "accept": "text/x-component",
        "accept-language": "vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5",
        "content-type": "text/plain;charset=UTF-8",
        "next-action": "f6a37f3b9ffdb01ba2da16f264fdabab4a254f61",
        "next-router-state-tree": "[\"\",{\"children\":[\"functions\",{\"children\":[\"text-to-speech\",{\"children\":[\"__PAGE__\",{},\"/text-to-speech\",\"refresh\"]}]}]}]",
        "origin": "https://freetts.com",
        "priority": "u=1, i",
        "referer": "https://freetts.com/text-to-speech",
        "sec-ch-ua": "\"Not(A:Brand\";v=\"99\", \"Google Chrome\";v=\"133\", \"Chromium\";v=\"133\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Cookie": "_ga=GA1.1.1605508501.1741007918; ... (Cookie cắt gọn) ..."
    }

    payload = [{
        "text": segment,
        "type": 0,
        "ssml": 0,
        "voiceType": "WaveNet",
        "languageCode": "vi-VN",
        "voiceName": "vi-VN-Wavenet-C",
        "gender": "FEMALE",
        "speed": "1.0",
        "pitch": "0",
        "volume": "0",
        "format": "mp3",
        "quality": 0,
        "isListenlingMode": 0,
        "displayName": "Veronica Chan"
    }]

    data = json.dumps(payload)

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, data=data) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Lỗi khi gọi API tạo audio: status {response.status}, response: {text}")

            # 1) Đọc toàn bộ phản hồi dưới dạng text
            text_response = await response.text()

            return extract_audio_url(text_response)


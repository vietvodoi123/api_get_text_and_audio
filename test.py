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

# Ví dụ bạn có mảng audio_urls:
audio_urls = [
    """0:["$@1",["84cax6OBoTQBQZ1A2WV_h",null]]
1:{"message":"","data":{"audiourl":"https://freetts.com/results/Yj7lDuPG.mp3","downloadCount":2370,"duration":0,"isListenlingMode":0},"code":200}
""",
    """0:["$@1",["84cax6OBoTQBQZ1A2WV_h",null]]
1:{"message":"","data":{"audiourl":"https://freetts.com/results/GU3groDR.mp3","downloadCount":2370,"duration":0,"isListenlingMode":0},"code":200}
"""
    # ...
]

# Ta tạo mảng mới chỉ chứa link audiourl
only_urls = [extract_audio_url(item) for item in audio_urls]

print(only_urls)
# Kết quả mong muốn: ["https://freetts.com/results/Yj7lDuPG.mp3", "https://freetts.com/results/GU3groDR.mp3", ...]

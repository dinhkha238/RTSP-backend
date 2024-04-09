import os
import threading
import subprocess

def cut_ip_address(url):
    start_index = url.find('@') + 1
    end_index = url.find('/', start_index)
    ip_address = url[start_index:end_index]
    ip_address = ip_address.replace(":", "_")
    return ip_address

def convert_to_hls(rtsp_url: str, _: str):
    if not os.path.exists(os.path.join("videos",cut_ip_address(rtsp_url))):
        os.makedirs(os.path.join("videos",cut_ip_address(rtsp_url)))
    output_m3u8 = os.path.join("videos",cut_ip_address(rtsp_url), "output.m3u8")
    subprocess.run([
    "ffmpeg",
    "-rtsp_transport", "tcp",
    "-i", rtsp_url,
    "-c:v", "copy",
    "-c:a", "aac",
    "-tag:v", "hvc1",  # Xác định tag:v là 'hvc1' cho codec HEVC
    "-f", "hls",
    "-hls_time", "4",  # Thay đổi từ 7 giây thành 2 giây
    "-hls_list_size", "4",
    "-hls_flags", "delete_segments",
    "-max_muxing_queue_size", "1024",
    "-start_number", "1",  # Thêm tham số để bắt đầu với số phân đoạn là 1
    output_m3u8
], check=True)

def thread_exists(thread_name):
    print(thread_name)
    for thread in threading.enumerate():
        if thread.name == thread_name:
            return True
    return False

def cleanup_folder(folder_path):
    if not os.path.exists(os.path.join("videos",folder_path)):
        return
    files = os.listdir(os.path.join("videos",folder_path))
    for file_name in files:
        file_path = os.path.join(os.path.join("videos",folder_path), file_name)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)  # Sử dụng os.remove để xóa tệp
        except Exception as e:
            print(f"Failed to delete {file_path}: {e}")
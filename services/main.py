import os
import subprocess
import cv2

def cut_ip_address(url):
    start_index = url.find('@') + 1
    end_index = url.find('/', start_index)
    ip_address = url[start_index:end_index]
    ip_address = ip_address.replace(":", "_")
    return ip_address

def convert_to_hls(rtsp_url: str, running_processes):
    if check_rtsp_online(rtsp_url):
        print("RTSP is online.")
        if not os.path.exists(os.path.join("videos",cut_ip_address(rtsp_url))):
            os.makedirs(os.path.join("videos",cut_ip_address(rtsp_url)))
        output_m3u8 = os.path.join("videos",cut_ip_address(rtsp_url), "output.m3u8")
        process = subprocess.Popen([
            "ffmpeg",
            "-rtsp_transport", "tcp",
            "-i", rtsp_url,
            "-c:v", "copy",
            "-c:a", "aac",
            "-tag:v", "hvc1",  
            "-f", "hls",
            "-hls_time", "4",  
            "-hls_list_size", "4",
            "-hls_flags", "delete_segments",
            "-max_muxing_queue_size", "1024",
            "-start_number", "1",  
            output_m3u8
        ])
        running_processes[cut_ip_address(rtsp_url)] = process
    else:
        print("RTSP is offline.")

def thread_exists(thread_name,running_processes):
    if thread_name in running_processes:
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

# Function to stop a running process
def stop_ffmpeg_by_ip(ip_cam,running_processes):
    if ip_cam in running_processes:
        process = running_processes[ip_cam]
        process.terminate()
        del running_processes[ip_cam]
        cleanup_folder(ip_cam)
        return {"message": f"Process for {ip_cam} has been terminated."}
    else:
        return {"message": f"No process found for {ip_cam}."}

def check_rtsp_online(rtsp_url):
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        return False
    else:
        return True
import os
import subprocess

from dotenv import load_dotenv
import cv2
import ffmpeg
from minio import Minio
from minio.error import S3Error

load_dotenv()


# Thông tin kết nối đến MinIO
minio_endpoint = os.environ.get('SECURITY_MINIO_ENDPOINT')
minio_access_key = os.environ.get('SECURITY_MINIO_ACCESS_KEY')
minio_secret_key = os.environ.get('SECURITY_MINIO_SECRET_KEY')

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
    minio_bucket_name = "rtsp"
    minio_client = Minio(minio_endpoint,
                        access_key=minio_access_key,
                        secret_key=minio_secret_key,
                        secure=False)
    if ip_cam in running_processes:
        process = running_processes[ip_cam]
        process.terminate()
        del running_processes[ip_cam]
        files = os.listdir(os.path.join("videos",ip_cam))
        last_video_file = os.path.join("videos", ip_cam, files[-1])
        cut_image_from_video(minio_client,minio_bucket_name,last_video_file,ip_cam)
        url = get_url(minio_client, minio_bucket_name, ip_cam + "_image_lastest.jpg")
        cleanup_folder(ip_cam)
        return url
    else:
        return None

def check_rtsp_online(rtsp_url):
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        return False
    else:
        return True
    
def cut_image_from_video(minio_client,minio_bucket_name,video_file_path,ip_cam):
    # Sử dụng ffmpeg để cắt ảnh từ video
    (
        ffmpeg.input(video_file_path)
        .output(os.path.join("videos",ip_cam,"image_lastest.jpg"), vframes=1, format='image2', vf='select=eq(n\,0)')
        .run()
    )
    try:
        if not minio_client.bucket_exists(minio_bucket_name):
            minio_client.make_bucket(minio_bucket_name)
        minio_client.fput_object(minio_bucket_name, ip_cam + "_image_lastest.jpg", os.path.join("videos",ip_cam,"image_lastest.jpg"))
        print("File uploaded successfully!")
    except S3Error as err:
        print(err)

def get_url(minio_client, bucket, name_file):
        url = minio_client.presigned_get_object(
                bucket, name_file 
            )
        return url

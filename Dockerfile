FROM python:3.11

# Cài đặt ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Đặt thư mục làm việc mặc định
WORKDIR /app

# Sao chép tất cả các tệp từ thư mục hiện tại của bạn vào thư mục /app trong container
COPY . .

# Cài đặt các gói Python từ requirements.txt
RUN pip install -r requirements.txt

# CMD để chạy ứng dụng của bạn khi container được khởi động
CMD ["python", "main.py"]

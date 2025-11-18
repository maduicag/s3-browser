# S3 Browser Web App

A lightweight **web-based S3 browser** built with Flask and Boto3. Browse buckets, navigate directories, search objects, and download files from S3-compatible storage.

## Features

- Login with **endpoint, access key, and secret key**
- Browse **buckets and folders**
- **Search objects** by prefix
- **Download files**
- Pagination and **back navigation**

## Compatibility

Works with any **S3-compatible storage**, including:

- AWS S3
- Ceph RADOS Gateway
- MinIO
- Other S3-compatible object storage

## Installation

1. Clone the repository:

```bash
git clone https://github.com/maduicag/s3-browser.git
cd s3-browser


2. Run the application:
python app.py

3. Open your browser:

http://localhost:5000
# S3 Browser Web App

A lightweight **web-based S3 browser** built with Flask and Boto3. Browse buckets, navigate directories, search objects, **upload and download files** from S3-compatible storage.

Dockerhub: https://hub.docker.com/r/maduica/s3arch
---

## Features

- Login with **endpoint, access key, and secret key**
- Browse **buckets and folders**
- **Search objects** by prefix
- **Upload files** to any bucket or folder
- **Download files** from buckets
- Pagination and **back navigation**

---

## Compatibility

Works with any **S3-compatible storage**, including:

- AWS S3
- Ceph RADOS Gateway
- MinIO
- Other S3-compatible object storage

---

## Installation

1. Clone the repository:

```bash
git clone https://github.com/maduicag/s3-browser.git
cd s3-browser


2. Install dependencies:
pip install flask boto3


3. Run the application:
python app.py

4. Open your browser and navigate to:
http://localhost:5000




Usage
1. Login

Enter your S3 endpoint, access key, and secret key.

Click Login.

2. Browse Buckets and Folders

Select a bucket from the dropdown.

Navigate folders by clicking on folder names.

Use the Back button to go to the previous folder.

3. Search Objects

Enter a prefix or partial object name in the search box.

Click Search to filter objects in the current bucket.

4. Upload Files

Select a bucket and folder where you want to upload.

Click Choose File to select a local file.

Click Upload to send the file to the S3 bucket.

A progress bar shows upload status.

5. Download Files

Click Download next to a file to save it locally.

Notes

The app works with any S3-compatible storage, not only AWS.

For large buckets, pagination is supported to load objects incrementally.

All interactions happen in the browser without exposing your credentials to other

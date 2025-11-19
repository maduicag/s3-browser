from flask import Flask, render_template, request, redirect, session, jsonify, send_file
import boto3
from botocore.config import Config
from io import BytesIO
import os

import logging

# Configure logging to file and console

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("s3browser.log"), logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

# ----------------------------
# Flask App Configuration
# ----------------------------
app = Flask(__name__)
# NOTE: Change this secret key before production!
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-key-change-this")

# ----------------------------
# Helper: Create S3 Client
# ----------------------------
def get_s3():
    """
    Returns a boto3 S3 client using credentials stored in the session.
    Returns None if credentials are not available.
    """
    if "access_key" not in session:
        return None

    return boto3.client(
        "s3",
        endpoint_url=session.get("endpoint"),
        aws_access_key_id=session.get("access_key"),
        aws_secret_access_key=session.get("secret_key"),
        config=Config(signature_version="s3v4")
    )

# ----------------------------
# LOGIN ROUTE
# ----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Handles user login to S3.
    GET: Render login page
    POST: Validate credentials and save them in session
    """
    if request.method == "GET":
        return render_template("login.html")

    # Retrieve form data
    endpoint = request.form.get("endpoint", "").strip()
    access_key = request.form.get("access_key", "").strip()
    secret_key = request.form.get("secret_key", "").strip()

    # Test provided credentials
    try:
        test_client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4")
        )
        # Attempt to list buckets to validate credentials
        test_client.list_buckets()
    except Exception as e:
        # Invalid credentials or endpoint
        return render_template("login.html", error="Invalid credentials or endpoint!")

    # Save validated credentials to session
    session["endpoint"] = endpoint
    session["access_key"] = access_key
    session["secret_key"] = secret_key

    return redirect("/")

# ----------------------------
# LOGOUT ROUTE
# ----------------------------
@app.route("/logout")
def logout():
    """
    Clears session data and redirects to login page.
    """
    session.clear()
    return redirect("/login")

# ----------------------------
# MAIN PAGE ROUTE
# ----------------------------
@app.route("/")
def index():
    """
    Main page showing all available S3 buckets.
    Redirects to login if no credentials are stored.
    """
    s3 = get_s3()
    if not s3:
        return redirect("/login")

    buckets = s3.list_buckets().get("Buckets", [])
    return render_template("index.html", buckets=buckets)

# ----------------------------
# LIST OBJECTS ROUTE
# ----------------------------
@app.route("/objects")
def objects():
    """
    Returns JSON list of objects in a specified bucket and prefix.
    Supports pagination using ContinuationToken.
    """
    s3 = get_s3()
    if not s3:
        return jsonify({"error": "not logged in"}), 401

    bucket = request.args.get("bucket")
    prefix = request.args.get("prefix", "")
    cursor = request.args.get("cursor")

    # S3 list_objects_v2 parameters
    params = {"Bucket": bucket, "Prefix": prefix, "MaxKeys": 100}  # Limit 100 per request
    if cursor:
        params["ContinuationToken"] = cursor

    try:
        result = s3.list_objects_v2(**params)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "objects": result.get("Contents", []),
        "next_cursor": result.get("NextContinuationToken")
    })

# ----------------------------
# SEARCH OBJECTS ROUTE
# ----------------------------
@app.route("/search")
def search():
    """
    Searches objects in a bucket by prefix (simple search).
    Returns JSON list of matching objects.
    """
    s3 = get_s3()
    if not s3:
        return jsonify({"error": "not logged in"}), 401

    bucket = request.args.get("bucket")
    q = request.args.get("q", "")

    if not q:
        return jsonify([])

    try:
        result = s3.list_objects_v2(Bucket=bucket, Prefix=q)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(result.get("Contents", []))

# ----------------------------
# DOWNLOAD OBJECT ROUTE
# ----------------------------
@app.route("/download")
def download():
    """
    Downloads a specific object from S3 and returns as an attachment.
    """
    s3 = get_s3()
    if not s3:
        return redirect("/login")

    bucket = request.args.get("bucket")
    key = request.args.get("key")

    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        data = obj["Body"].read()
    except Exception as e:
        return "Error fetching object: {}".format(str(e)), 500

    return send_file(
        BytesIO(data),
        as_attachment=True,
        download_name=key.split("/")[-1]
    )

# ----------------------------
# UPLOAD ROUTE
# ----------------------------


from io import BytesIO
from boto3.s3.transfer import TransferConfig

def get_s3_for_upload():
    """
    Returns a boto3 client configured specifically for uploads to Ceph RGW.
    """
    if "access_key" not in session:
        return None

    from botocore.client import Config

    return boto3.client(
        "s3",
        endpoint_url=session.get("endpoint"),
        aws_access_key_id=session.get("access_key"),
        aws_secret_access_key=session.get("secret_key"),
        config=Config(signature_version="s3")  # S3 v2 semnătura, compatibil Ceph
    )

@app.route("/upload", methods=["POST"])
def upload():
    s3 = get_s3_for_upload()
    if not s3:
        return jsonify({"error": "not logged in"}), 401

    file = request.files.get("file")
    bucket = request.form.get("bucket")
    prefix = request.form.get("prefix", "")
    key = prefix + file.filename

    if not file or not bucket:
        return jsonify({"error": "file or bucket missing"}), 400

    try:
        # Citim fișierul în memorie
        content = file.read()
        file_size = len(content)
        file_stream = BytesIO(content)

        logging.info(f"Uploading file {file.filename} to bucket {bucket}, key {key}, size {file_size} bytes")

        # TransferConfig optional, dar nu e strict necesar pentru fișiere mici
        config = TransferConfig(
            multipart_threshold=5*1024*1024,
            multipart_chunksize=5*1024*1024
        )

        # Reset pointer
        file_stream.seek(0)
        s3.upload_fileobj(
            Fileobj=file_stream,
            Bucket=bucket,
            Key=key,
            Config=config
        )

        logging.info(f"Upload successful for {file.filename}")
        return jsonify({"success": True, "key": key}), 200

    except Exception as e:
        logging.error(f"Upload failed for {file.filename}: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ----------------------------
# DELETE ROUTE
# ----------------------------
@app.route("/delete", methods=["POST"])
def delete():
    """
    Delete a file from the specified bucket.
    Expects form-data: bucket, key
    """
    s3 = get_s3()
    if not s3:
        return jsonify({"error": "not logged in"}), 401

    bucket = request.form.get("bucket")
    key = request.form.get("key")

    if not bucket or not key:
        return jsonify({"error": "bucket and key are required"}), 400

    try:
        s3.delete_object(Bucket=bucket, Key=key)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------------------------
# RUN APP
# ----------------------------
if __name__ == "__main__":
    # Flask runs in debug mode by default for development
    # Change host/port as needed for production
    app.run(host="0.0.0.0", port=5001, debug=True)

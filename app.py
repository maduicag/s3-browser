from flask import Flask, render_template, request, redirect, session, jsonify, send_file
import boto3
from botocore.config import Config
from io import BytesIO

# ----------------------------
# Flask App Configuration
# ----------------------------
app = Flask(__name__)
# NOTE: Change this secret key before production!
app.secret_key = "super-secret-key-change-this"  

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
        endpoint_url=session["endpoint"],
        aws_access_key_id=session["access_key"],
        aws_secret_access_key=session["secret_key"],
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
    endpoint = request.form.get("endpoint").strip()
    access_key = request.form.get("access_key").strip()
    secret_key = request.form.get("secret_key").strip()

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
        return redirect("/login")

    bucket = request.args.get("bucket")
    prefix = request.args.get("prefix", "")
    cursor = request.args.get("cursor")

    # S3 list_objects_v2 parameters
    params = {"Bucket": bucket, "Prefix": prefix, "MaxKeys": 100}  # Limit 100 per request
    if cursor:
        params["ContinuationToken"] = cursor

    result = s3.list_objects_v2(**params)

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
        return redirect("/login")

    bucket = request.args.get("bucket")
    q = request.args.get("q", "")

    if not q:
        return jsonify([])

    result = s3.list_objects_v2(Bucket=bucket, Prefix=q)

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

    obj = s3.get_object(Bucket=bucket, Key=key)
    data = obj["Body"].read()

    return send_file(
        BytesIO(data),
        as_attachment=True,
        download_name=key.split("/")[-1]
    )

# ----------------------------
# RUN APP
# ----------------------------
if __name__ == "__main__":
    # Flask runs in debug mode by default for development
    # Change host/port as needed for production
    app.run(host="0.0.0.0", port=5000, debug=True)

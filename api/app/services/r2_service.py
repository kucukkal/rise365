import boto3
from botocore.config import Config
from app.config import settings
import io

def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )

def upload_pdf(file_content: bytes, filename: str) -> str:
    """Upload PDF to R2 and return the key"""
    client = get_r2_client()
    key = f"pdfs/{filename}"
    client.put_object(
        Bucket=settings.R2_BUCKET,
        Key=key,
        Body=file_content,
        ContentType="application/pdf",
    )
    print(f"✅ Uploaded to R2: {key}")
    return key

def download_pdf(filename: str) -> bytes:
    """Download PDF from R2"""
    client = get_r2_client()
    key = f"pdfs/{filename}"
    try:
        response = client.get_object(
            Bucket=settings.R2_BUCKET,
            Key=key,
        )
        return response["Body"].read()
    except Exception as e:
        print(f"❌ R2 download error for {key}: {e}")
        raise

def pdf_exists_in_r2(filename: str) -> bool:
    """Check if PDF exists in R2"""
    client = get_r2_client()
    key = f"pdfs/{filename}"
    try:
        client.head_object(Bucket=settings.R2_BUCKET, Key=key)
        return True
    except:
        return False

def upload_existing_pdfs():
    """Upload all existing local PDFs to R2"""
    import os
    from app.services.pdf_service import PDF_DIR
    
    if not os.path.exists(PDF_DIR):
        print("No local PDFs found")
        return
    
    files = os.listdir(PDF_DIR)
    pdfs = [f for f in files if f.endswith('.pdf')]
    print(f"Found {len(pdfs)} PDFs to upload...")
    
    for i, filename in enumerate(pdfs, 1):
        filepath = os.path.join(PDF_DIR, filename)
        if pdf_exists_in_r2(filename):
            print(f"⏭️  {i}/{len(pdfs)} Already in R2: {filename}")
            continue
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            upload_pdf(content, filename)
            print(f"✅ {i}/{len(pdfs)} Uploaded: {filename}")
        except Exception as e:
            print(f"❌ {i}/{len(pdfs)} Failed {filename}: {e}")
    
    print("✅ Done uploading PDFs to R2!")

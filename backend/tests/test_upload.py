import io
import json
import urllib.request

boundary = "----TestBoundary98765"
pdf_content = (
    "Abhimanyu Panda\n"
    "abhimanyu.panda@gmail.com\n"
    "+91-9876543210\n"
    "Bengaluru, Karnataka, India\n"
    "Senior Backend Software Engineer with 4.5 years of experience in Python, FastAPI, GCP, Kubernetes, Docker, PostgreSQL, Redis, Kafka.\n"
    "Past Companies: Swiggy, Google\n"
    "Education: B.Tech Computer Science\n"
)

body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="Abhimanyu_Panda_Resume.pdf"\r\n'
    f"Content-Type: application/pdf\r\n\r\n"
    f"{pdf_content}\r\n"
    f"--{boundary}--\r\n"
).encode("utf-8")

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/auth/upload-resume",
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    method="POST"
)

try:
    with urllib.request.urlopen(req) as resp:
        print(f"Status Code: {resp.getcode()}")
        data = json.loads(resp.read().decode("utf-8"))
        print(f"Parsed Name: {data['user']['name']}")
        print(f"Parsed Email: {data['user']['email']}")
        print(f"Parsed Role: {data['user']['currentRole']}")
        print(f"Parsed Exp: {data['user']['experienceYears']} years")
        print(f"Parsed Skills: {data['user']['skills']}")
        print(f"Message: {data['message']}")
except Exception as e:
    print(f"Error: {e}")

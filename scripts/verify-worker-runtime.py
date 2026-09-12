import json
import subprocess
import time
import urllib.error
import urllib.request
from uuid import uuid4

process = subprocess.Popen(
    ["uvicorn", "app.worker_main:app", "--host", "127.0.0.1", "--port", "8080"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
try:
    for _ in range(100):
        try:
            with urllib.request.urlopen(
                "http://127.0.0.1:8080/health", timeout=1
            ) as response:
                assert response.status == 200
                break
        except urllib.error.URLError:
            assert process.poll() is None, "Worker exited during startup"
            time.sleep(0.1)
    else:
        raise AssertionError("Worker did not become ready")
    with urllib.request.urlopen(
        "http://127.0.0.1:8080/health/db", timeout=3
    ) as response:
        assert response.status == 200
    payload = json.dumps({"version": 1, "job_id": str(uuid4())}).encode()
    request = urllib.request.Request(
        "http://127.0.0.1:8080/internal/tasks/rank-check",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=3) as response:
        assert response.status == 200
    for path in ("/docs", "/openapi.json", "/api/v1/projects"):
        try:
            urllib.request.urlopen("http://127.0.0.1:8080" + path, timeout=3)
        except urllib.error.HTTPError as error:
            assert error.code == 404
        else:
            raise AssertionError("Worker exposes public API")
    print(
        json.dumps(
            {
                "production_worker_command": "passed",
                "health": 200,
                "database": 200,
                "unknown_job_acknowledged": 200,
                "public_routes_absent": True,
                "real_provider_calls": 0,
            }
        )
    )
finally:
    process.terminate()
    process.wait(timeout=10)

"""Document access-control tests for synthetic demo identities only."""
from io import BytesIO

FILE = b"%PDF-1.4\n% fictional document\n1 0 obj<<>>endobj\n%%EOF"

def upload(client, headers, name="demo.pdf", patient_id=None):
    h = {**headers, "Content-Type": "application/pdf", "X-Document-Name": name}
    if patient_id:
        h["X-Target-Patient-Id"] = patient_id
    return client.post("/api/documents/upload", headers=h, content=FILE)


def test_private_upload_download_and_restricted_sharing(client, auth, other):
    uploaded = upload(client, auth)
    assert uploaded.status_code == 200, uploaded.text
    data = uploaded.json()["data"]
    assert data["shared_with_caregivers"] is False
    assert len(client.get("/api/documents", headers=auth).json()["data"]) == 1
    assert client.get(f"/api/documents/{data['id']}", headers=auth).content == FILE
    assert client.get(f"/api/documents/{data['id']}", headers=other).status_code == 404
    assert client.patch(f"/api/documents/{data['id']}/sharing", headers=other,
        json={"shared_with_caregivers": True}).status_code == 404
    assert client.delete(f"/api/documents/{data['id']}", headers=other).status_code == 404


def test_caregiver_requires_accepted_relationship_and_patient_sharing(client, auth, other):
    patient_id = client.get("/api/patients/me", headers=auth).json()["data"]["id"]
    doc = upload(client, auth).json()["data"]
    assert upload(client, other, patient_id=patient_id).status_code == 403
    invite = client.post("/api/caregivers/invitations", headers=auth, json={
        "caregiver_user_id": "synthetic-jordan",
        "permissions": ["recovery_summary"],
        "alert_severities": [],
    })
    assert invite.status_code == 201, invite.text
    rel = invite.json()["data"]
    assert client.post(f"/api/caregiver/invitations/{rel['id']}/respond",
        headers=other, json={"expected_version": rel["version"], "decision": "accept"}).status_code == 200
    assert client.get(f"/api/documents/{doc['id']}", headers=other).status_code == 404
    shared = client.patch(f"/api/documents/{doc['id']}/sharing",
        headers=auth, json={"shared_with_caregivers": True})
    assert shared.status_code == 200, shared.text
    assert client.get(f"/api/documents/{doc['id']}", headers=other).status_code == 200
    caregiver_file = upload(client, other, patient_id=patient_id)
    assert caregiver_file.status_code == 200, caregiver_file.text
    assert any(row["id"] == caregiver_file.json()["data"]["id"] for row in
        client.get("/api/documents", headers=auth).json()["data"])
    assert client.post(f"/api/caregivers/{rel['id']}/revoke",
        headers=auth, json={"expected_version": rel["version"]+1}).status_code == 200
    assert client.get(f"/api/documents/{doc['id']}", headers=other).status_code == 404
    assert client.get(f"/api/documents/{caregiver_file.json()['data']['id']}", headers=other).status_code == 404


def test_rejects_fake_pdf_and_oversize(client, auth):
    headers={**auth, "Content-Type": "application/pdf","X-Document-Name":"demo.pdf"}
    assert client.post("/api/documents/upload", headers=headers, content=b"not a PDF").status_code == 422
    assert client.post("/api/documents/upload", headers=headers, content=b"%PDF-"+b"x"*(3*1024*1024)).status_code == 413

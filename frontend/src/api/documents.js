import { request } from './client';

// Single fixed project for v1 (DECISIONS.md 011) - hardcoded here so
// it's one place to change if that ever stops being true.
const PROJECT_ID = 1;

export async function listDocuments() {
  return request(`/projects/${PROJECT_ID}/documents`, {
    method: 'GET',
  });
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);

  // No explicit Content-Type here - axios sets multipart/form-data
  // with the correct boundary automatically when given a FormData body.
  return request(`/projects/${PROJECT_ID}/documents`, {
    method: 'POST',
    data: formData,
  });
}
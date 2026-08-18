import { request } from './client';

const PROJECT_ID = 1;

export async function listConversations() {
  return request(`/projects/${PROJECT_ID}/conversations`, {
    method: 'GET',
  });
}

export async function createConversation(title = null) {
  return request(`/projects/${PROJECT_ID}/conversations`, {
    method: 'POST',
    data: { title },
  });
}

export async function listMessages(conversationId) {
  return request(`/conversations/${conversationId}/messages`, {
    method: 'GET',
  });
}

export async function sendMessage(conversationId, content) {
  return request(`/conversations/${conversationId}/messages`, {
    method: 'POST',
    data: { content },
  });
}
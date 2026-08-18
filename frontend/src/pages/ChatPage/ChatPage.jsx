import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { listMessages, sendMessage } from '../../api/conversations';
import CitationText from '../../components/CitationText/CitationText';
import './ChatPage.css';

export default function ChatPage() {
    const { conversationId } = useParams();
    const queryClient = useQueryClient();
    const [draft, setDraft] = useState('');
    const [sendError, setSendError] = useState(null);

    const {
        data: messages,
        isPending,
        isError,
        error,
    } = useQuery({
        queryKey: ['messages', conversationId],
        queryFn: () => listMessages(conversationId),
    });

    const sendMutation = useMutation({
        mutationFn: (content) => sendMessage(conversationId, content),
        onSuccess: () => {
            setSendError(null);
            // Backend persisted both the user question and assistant reply -
            // refetch to get the full, accurate thread instead of guessing at it.
            setDraft('')
            queryClient.invalidateQueries({ queryKey: ['messages', conversationId] });
        },
        onError: (err) => {
            // Per DECISIONS.md 019, the user's question was NOT persisted on
            // failure - so we do NOT clear the draft here. Keep it in the
            // input so the user can just hit send again without retyping.
            setSendError(err.message);
        },
    });

    function handleSend(e) {
        e.preventDefault();
        const trimmed = draft.trim();
        if (!trimmed) return;
        sendMutation.mutate(trimmed);
    }

    const isSending = sendMutation.isPending;

    return (
        <div className="chat-page">
            <div className="chat-thread">
                {isPending && <p>Loading conversation...</p>}

                {isError && (
                    <p role="alert" className="error-text">
                        Failed to load conversation: {error.message}
                    </p>
                )}

                {messages && messages.length === 0 && (
                    <p className="empty-state">No messages yet — ask something below to get started.</p>
                )}

                {messages?.map((msg) => (
                    <div key={msg.id} className={`message message--${msg.role}`}>
                        {msg.role === 'assistant' ?
                            (
                                <CitationText content={msg.content} references={msg.references} />
                            )
                            : (
                                <p>{msg.content}</p>
                            )}
                    </div>
                ))}

                {isSending && (
                    <div className="message message--assistant message--pending">
                        <span className="spinner" aria-hidden="true" />
                        <span>Thinking...</span>
                    </div>
                )}
            </div>

            {sendError && (
                <div className="send-error" role="alert">
                    <span>Message failed: {sendError}</span>
                    <button type="button" onClick={() => sendMutation.mutate(draft.trim())}>
                        Retry
                    </button>
                </div>
            )}

            <form className="chat-input-row" onSubmit={handleSend}>
                <input
                    type="text"
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    placeholder="Ask a question..."
                    disabled={isSending}
                />
                <button type="submit" disabled={isSending || !draft.trim()}>
                    Send
                </button>
            </form>
        </div>
    );
}
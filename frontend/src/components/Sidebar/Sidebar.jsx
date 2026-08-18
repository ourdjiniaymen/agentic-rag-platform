import { NavLink, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listConversations, createConversation } from '../../api/conversations';
import './Sidebar.css';

function Sidebar() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: conversations, isPending, isError } = useQuery({
    queryKey: ['conversations'],
    queryFn: listConversations,
  });

  const createMutation = useMutation({
    mutationFn: () => createConversation(),
    onSuccess: (newConversation) => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      navigate(`/chat/${newConversation.id}`);
    },
  });

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="sidebar-title">RAG Platform</span>
      </div>

      <nav className="sidebar-nav">
        <NavLink to="/" end className="sidebar-link">
          Documents
        </NavLink>
      </nav>

      <div className="sidebar-section">
        <div className="sidebar-section-header">
          <span className="sidebar-section-title">Conversations</span>
          <button
            type="button"
            className="new-chat-btn"
            onClick={() => createMutation.mutate()}
            disabled={createMutation.isPending}
          >
            + New
          </button>
        </div>

        <nav className="sidebar-nav">
          {isPending && <span className="sidebar-hint">Loading...</span>}
          {isError && <span className="sidebar-hint">Failed to load</span>}
          {conversations && conversations.length === 0 && (
            <span className="sidebar-hint">No conversations yet</span>
          )}
          {[...(conversations ?? [])]
            .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
            .map((conv) => (
              <NavLink key={conv.id} to={`/chat/${conv.id}`} className="sidebar-link">
                {conv.title || `Conversation ${conv.id}`}
              </NavLink>
            ))}
        </nav>
      </div>
    </aside>
  );
}

export default Sidebar
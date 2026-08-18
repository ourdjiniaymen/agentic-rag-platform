import { useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { listDocuments, uploadDocument } from '../../api/documents';
import StatusBadge from '../../components/StatusBadge/StatusBadge';
import './DocumentsPage.css';

export default function DocumentsPage() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef(null);
  const [uploadError, setUploadError] = useState(null);
  const [pendingFilename, setPendingFilename] = useState(null);

  const {
    data: documents,
    isPending,
    isError,
    error,
  } = useQuery({
    queryKey: ['documents'],
    queryFn: listDocuments,
  });

  const uploadMutation = useMutation({
    mutationFn: uploadDocument,
    onSuccess: () => {
      setPendingFilename(null);
      // Table is now stale - refetch so the new/updated row shows up.
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
    onError: (err) => {
      setPendingFilename(null);
      setUploadError(err.message);
    },
  });

  function handleFileChosen(file) {
    if (!file) return;
    setUploadError(null);
    setPendingFilename(file.name);
    uploadMutation.mutate(file);
  }

  function handleInputChange(e) {
    handleFileChosen(e.target.files[0]);
    e.target.value = ''; // allow re-selecting the same file later
  }

  function handleDrop(e) {
    e.preventDefault();
    handleFileChosen(e.dataTransfer.files[0]);
  }

  const isUploading = uploadMutation.isPending;

  return (
    <div>
      <h1>Documents</h1>
      <p className="page-subtitle">Manage and index knowledge base files.</p>

      <input
        ref={fileInputRef}
        type="file"
        accept="application/pdf"
        onChange={handleInputChange}
        hidden
      />

      <button
        className="upload-dropzone"
        type="button"
        disabled={isUploading}
        onClick={() => fileInputRef.current.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        {isUploading ? 'Upload in progress...' : 'Click to upload or drag and drop'}
        <span className="upload-hint">PDF up to 50MB</span>
      </button>

      {isUploading && (
        <div className="upload-status upload-status--pending">
          <span className="spinner" aria-hidden="true" />
          <span>{pendingFilename} — indexing...</span>
        </div>
      )}

      {uploadError && (
        <div className="upload-status upload-status--error" role="alert">
          <span>Upload failed: {uploadError}</span>
          <button type="button" className="dismiss-btn" onClick={() => setUploadError(null)}>
            ×
          </button>
        </div>
      )}

      <div className="documents-card">
        {isPending && <p>Loading documents...</p>}

        {isError && (
          <p role="alert" className="error-text">
            Failed to load documents: {error.message}
          </p>
        )}

        {documents && documents.length === 0 && (
          <p className="empty-state">No documents yet — upload a PDF to get started.</p>
        )}

        {documents && documents.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Filename</th>
                <th>Status</th>
                <th>Pages</th>
                <th>Chunks</th>
                <th>Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id}>
                  <td>{doc.filename}</td>
                  <td>
                    <StatusBadge status={doc.status} />
                  </td>
                  <td>{doc.page_count ?? '-'}</td>
                  <td>{doc.chunk_count ?? '-'}</td>
                  <td>{new Date(doc.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
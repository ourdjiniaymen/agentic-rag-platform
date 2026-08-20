import { useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { listDocuments, uploadDocument } from '../../api/documents';
import StatusBadge from '../../components/StatusBadge/StatusBadge';
import './DocumentsPage.css';

export default function DocumentsPage() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef(null);
  const [pendingFiles, setPendingFiles] = useState([])
  const [uploadErrors, setUploadErrors] = useState([])

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
    onSuccess: (_, file) => {
      // file = the file passed to mutate(file)
      setPendingFiles(prev => prev.filter(f => f !== file));
      // Table is now stale - refetch so the new/updated row shows up.
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },

    onError: (err, file) => {
      // file = the file passed to mutate(file)
      setPendingFiles(prev => prev.filter(f => f !== file));
      setUploadErrors(prev => [
        ...prev,
        [file, err]]
      );
    },
  });

  function handleFileChosen(file) {
    if (!file) return;
    setPendingFiles(prev => [...prev, file]);
    uploadMutation.mutate(file);
  }

  function handleInputChange(e) {
    console.log(e.target.files[0])
    handleFileChosen(e.target.files[0]);
    e.target.value = ''; // allow re-selecting the same file later
  }

  function handleDrop(e) {
    e.preventDefault();
    handleFileChosen(e.dataTransfer.files[0]);
  }


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
        onClick={() => fileInputRef.current.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
      
        Click to upload or drag and drop
        <span className="upload-hint">PDF up to 50MB</span>
      </button>

      {
        pendingFiles.map((file, i) => (
          <div key = {i} className="upload-status upload-status--pending">
            <span className="spinner" aria-hidden="true" />
            <span>{file.name} — indexing...</span>
          </div>
        ))
      }

      {
        uploadErrors.map(([file, error], i) => (
          <div  key={i} className="upload-status upload-status--error" role="alert">
            <span>Upload failed for {file.name}: {error.message}</span>
            <button type="button" className="dismiss-btn" onClick={() => { 
              setUploadErrors(prev => prev.filter((_,index)=>index !== i));
            }}>
              ×
            </button>
          </div>
        ))
      }

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